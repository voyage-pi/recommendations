import openai
import os
from typing import List, Dict
from pydantic import BaseModel
import json
from datetime import datetime, timedelta
from app.schemas.Activities import Activity, TripItinerary, DayItinerary

class OpenAIAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = self.api_key

    def generate_itinerary(self, itinerary: TripItinerary) -> TripItinerary:
        """
        Generate a schedule for each day in the itinerary and return the updated itinerary.
        
        Args:
            itinerary: The trip itinerary containing days and activities
            
        Returns:
            An updated itinerary with proposed scheduling for each day
        """
        # Custom function to handle datetime serialization
        def serialize_activity(activity):
            return {"name": activity.place.name}
        
        # Process each day in the itinerary
        for i, day in enumerate(itinerary.days):
            # Combine morning and afternoon activities for processing
            all_activities = day.morning_activities + day.afternoon_activities
            
            if not all_activities:
                continue  # Skip days with no activities
            
            # Format activities as JSON-serializable data
            activities_data = []
            for activity in all_activities:
                activity_dict = serialize_activity(activity)
                activities_data.append(activity_dict)

            
            # Create a properly formatted message with user role
            message = {
                "role": "user",
                "content": f"Create a daily schedule for {day.date.strftime('%Y-%m-%d')} based on these activities: {json.dumps(activities_data)}"
            }

            

            response = openai.responses.create(
                model="gpt-4o-mini-2024-07-18",
                input=[message],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "itinerary",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "activities": {
                                    "type": "array",
                                    "description": "A list of planned activities for the day.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "The name of the activity."
                                            },
                                            "duration": {
                                                "type": "string",
                                                "description": "Expected duration of the activity."
                                            },
                                            "start_time": {
                                                "type": "string",
                                                "description": "The start time for the activity in HH:MM format."
                                            },
                                            "end_time": {
                                                "type": "string",
                                                "description": "The end time for the activity in HH:MM format."
                                            }
                                        },
                                        "required": [
                                            "name",
                                            "duration",
                                            "start_time",
                                            "end_time"
                                        ],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": [
                                "activities"
                            ],
                            "additionalProperties": False
                        }
                    }
                },
                reasoning={},
                tools=[
                    {
                        "type": "web_search_preview",
                        "user_location": {
                            "city": "Lisbon",
                            "type": "approximate",
                            "region": "Lisbon",
                            "country": "PT"
                        },
                        "search_context_size": "low"
                    }
                ],
                tool_choice={
                    "type": "web_search_preview"
                },
                temperature=1,
                max_output_tokens=2048,
                top_p=1,
                store=True
            )

            print(f"Response: {response}")
            
            # Parse the response and update the activity times in the itinerary
            try:
                # Debug the response object type
                
                # Based on the actual OpenAI API response structure, extract the JSON
                scheduled_activities = []
                
                # The JSON is in response.output[1].content[0].text
                if hasattr(response, 'output') and isinstance(response.output, list):
                    # Find the message output (usually at index 1 after web search)
                    for output_item in response.output:
                        if hasattr(output_item, 'content') and isinstance(output_item.content, list):
                            for content_item in output_item.content:
                                if hasattr(content_item, 'text') and isinstance(content_item.text, str):
                                    # Found the text content, which contains the JSON
                                    text_content = content_item.text.strip()
                                    try:
                                        # Parse the JSON string
                                        data = json.loads(text_content)
                                        if isinstance(data, dict) and 'activities' in data:
                                            scheduled_activities = data['activities']
                                            break
                                    except json.JSONDecodeError as e:
                                        print(f"Error parsing JSON: {e}")
                                        print(f"Text content: {text_content[:100]}...")
                            
                            # If we found activities, break from the outer loop
                            if scheduled_activities:
                                break
                
                # If we still have nothing, print the full response
                if not scheduled_activities:
                    print(f"Could not extract activities from the response")
                    # Skip processing for this day
                    continue
                
                # Map scheduled activities back to the original activities
                for scheduled in scheduled_activities:
                    # Find matching activity by name
                    for activity in all_activities:
                        if activity.place.name.lower() in scheduled["name"].lower() or scheduled["name"].lower() in activity.place.name.lower():
                            # Parse start and end times
                            start_time_str = scheduled["start_time"]
                            end_time_str = scheduled["end_time"]
                            
                            # Update the activity with the scheduled times
                            activity_date = day.date.date()
                            start_hour, start_minute = map(int, start_time_str.split(":"))
                            end_hour, end_minute = map(int, end_time_str.split(":"))
                            
                            activity.start_time = datetime.combine(activity_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
                            activity.end_time = datetime.combine(activity_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
                            break
                
                # Re-sort morning and afternoon activities based on start time
                morning_activities = []
                afternoon_activities = []
                
                for activity in all_activities:
                    if activity.start_time.hour < 12:
                        morning_activities.append(activity)
                    else:
                        afternoon_activities.append(activity)
                
                # Sort by start time
                morning_activities.sort(key=lambda x: x.start_time)
                afternoon_activities.sort(key=lambda x: x.start_time)
                
                # Update the day's activities
                itinerary.days[i].morning_activities = morning_activities
                itinerary.days[i].afternoon_activities = afternoon_activities

                print(f"Updated itinerary: {itinerary}")
                
            except Exception as e:
                print(f"Error processing day {day.date}: {str(e)}")
        
        return itinerary