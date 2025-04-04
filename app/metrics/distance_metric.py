from app.models.scores import Metric
from typing import List,Tuple
from app.schemas.Activities import DayItinerary, PlaceInfo,TripItinerary,LatLong
from app.utils.distance_funcs import R, calculate_distance_lat_long
import numpy as np 
import math

class DistanceMetric(Metric):
    def __init__(self) -> None:
        super().__init__()


    def convert_lat_long_to_3d(self,coordinates:LatLong)->Tuple[float,float,float]:
        rad_theta=(coordinates.latitude * math.pi) / 180
        rad_phi= (coordinates.longitude * math.pi) / 180

        x = R *  math.cos(rad_phi)* math.sin(rad_theta)
        y = R *  math.sin(rad_theta)* math.sin(rad_phi)
        z= R * math.sin(rad_phi)
        return (x,y,z)

    def calculate_distance_matrix(self,places:List[PlaceInfo]):
        distance_matrix=[[-1.0 for i in range(len(places))] for j in range(len(places))]
        for c in range(len(places)):
            for r in range(c,len(places)):
                if r == c :
                    continue
                locationR:LatLong=places[r].location
                locationC:LatLong=places[c].location
                distance_matrix[r][c]=calculate_distance_lat_long(locationC,locationR)
                # distance_matrix[c][r]=distance_matrix[r][c]
        return distance_matrix

    def calculate_area_of_places(self,coordinates:List[LatLong])->float:
        assert(len(coordinates)>=3)
        n=len(coordinates)
        points=[]
        vectors=[]
        vector_normals=[]
        angles=[]
        #Convert all the points into 3d spheres coordinates
        for c in coordinates:
            points.append(self.convert_lat_long_to_3d(c))
        #calculate vectors
        for i in range(1,len(points)+1):
            a=(i-1)%len(points)
            b=(i)%len(points)
            v= (points[b][0]-points[a][0], points[b][1]-points[a][1],points[b][2]-points[a][2])
            vectors.append(v)
        #calculate all the angles between all the vectors 
        for vi in range(0,len(vectors)):
            vA=list(vectors[vi-1])
            vB=list(vectors[vi])
            vector_normals.append(np.cross(vA,vB))
        for ci in range(0,len(vector_normals)):
            n1=vector_normals[ci-1] 
            n2=vector_normals[ci]
            angles.append(np.dot(n1,n2))
        #calculate the area with SPA
        surface_area = (np.sum(angles)-(n-2)*math.pi) * R
        return surface_area

    def places_density_per_day(self,day:DayItinerary)->float:
        activities=day.morning_activities+day.afternoon_activities
        places = [a.place for a in activities]
        coordinates=[p.location for p in places] 
        area_covered_day= self.calculate_area_of_places(coordinates)
        return area_covered_day 

    # this metric for now only calculates the average coverage area of the places of all days of an itinerary
    def calculate(self, itinerary: TripItinerary) -> float:
        density_of_places= [self.places_density_per_day(d) for d in itinerary.days]
        return np.average(density_of_places)




