from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt
from .models import (
    ParkingSpot, CommercialParkingFacility, CommercialParkingSlot,
    PrivateParkingListing, PrivateParkingSlot
)
from .serializers import (
    ParkingSpotSerializer, ParkingSpotListSerializer,
    CommercialParkingFacilitySerializer, CommercialParkingFacilityListSerializer,
    CommercialParkingSlotSerializer,
    PrivateParkingListingSerializer, PrivateParkingListingListSerializer,
    PrivateParkingSlotSerializer
)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km * 1000  # Return in meters


class ParkingSpotViewSet(viewsets.ModelViewSet):
    queryset = ParkingSpot.objects.all()
    serializer_class = ParkingSpotSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['spot_type', 'is_occupied', 'has_cctv', 'is_covered', 'has_ev_charging', 'is_24_hours']
    search_fields = ['address']
    ordering_fields = ['price_per_hour', 'rating', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ParkingSpotListSerializer
        return ParkingSpotSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by price range
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price_per_hour__lte=max_price)
        
        # Filter by availability
        available_only = self.request.query_params.get('available_only')
        if available_only == 'true':
            queryset = queryset.filter(is_occupied=False, is_disabled=False)
        
        # Calculate distance if user location provided
        user_lat = self.request.query_params.get('lat')
        user_lon = self.request.query_params.get('lon')
        if user_lat and user_lon:
            spots_with_distance = []
            for spot in queryset:
                distance = calculate_distance(user_lat, user_lon, spot.latitude, spot.longitude)
                spot.distance = distance
                spots_with_distance.append(spot)
            
            # Sort by distance
            spots_with_distance.sort(key=lambda x: x.distance)
            return spots_with_distance
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get nearby parking spots"""
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = float(request.query_params.get('radius', 5000))  # 5km default
        
        if not lat or not lon:
            return Response({
                'error': 'Latitude and longitude required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        spots = self.get_queryset().filter(is_occupied=False, is_disabled=False)
        nearby_spots = []
        
        for spot in spots:
            distance = calculate_distance(lat, lon, spot.latitude, spot.longitude)
            if distance <= radius:
                spot.distance = distance
                nearby_spots.append(spot)
        
        nearby_spots.sort(key=lambda x: x.distance)
        serializer = ParkingSpotListSerializer(nearby_spots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_occupancy(self, request, pk=None):
        spot = self.get_object()
        spot.is_occupied = not spot.is_occupied
        spot.save()
        return Response({'status': 'occupied' if spot.is_occupied else 'available'})


class CommercialParkingFacilityViewSet(viewsets.ModelViewSet):
    queryset = CommercialParkingFacility.objects.all()
    serializer_class = CommercialParkingFacilitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['facility_type', 'has_cctv', 'has_ev_charging', 'has_valet_service', 'is_24_hours']
    search_fields = ['name', 'address']
    ordering_fields = ['default_hourly_rate', 'rating', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CommercialParkingFacilityListSerializer
        return CommercialParkingFacilitySerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Calculate distance if user location provided
        user_lat = self.request.query_params.get('lat')
        user_lon = self.request.query_params.get('lon')
        if user_lat and user_lon:
            facilities_with_distance = []
            for facility in queryset:
                distance = calculate_distance(user_lat, user_lon, facility.latitude, facility.longitude)
                facility.distance = distance
                facilities_with_distance.append(facility)
            
            # Sort by distance
            facilities_with_distance.sort(key=lambda x: x.distance)
            return facilities_with_distance
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def slots(self, request, pk=None):
        """Get all slots for a facility"""
        facility = self.get_object()
        slots = facility.slots.all()
        
        floor = request.query_params.get('floor')
        if floor:
            slots = slots.filter(floor=floor)
        
        slot_type = request.query_params.get('slot_type')
        if slot_type:
            slots = slots.filter(slot_type=slot_type)
        
        available_only = request.query_params.get('available_only')
        if available_only == 'true':
            slots = slots.filter(is_occupied=False, is_disabled=False)
        
        serializer = CommercialParkingSlotSerializer(slots, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def create_slots(self, request, pk=None):
        facility = self.get_object()
        try:
            count = int(request.data.get('count', 0))
            floor = int(request.data.get('floor', 1))
        except ValueError:
            return Response({'error': 'Invalid number format'}, status=status.HTTP_400_BAD_REQUEST)
            
        slot_type = request.data.get('slot_type', 'regular')
        
        existing_count = facility.slots.filter(floor=floor).count()
        slots = []
        for i in range(count):
            slots.append(CommercialParkingSlot(
                facility=facility,
                floor=floor,
                slot_type=slot_type,
                slot_number=f"F{floor}-{existing_count+i+1}"
            ))
            
        CommercialParkingSlot.objects.bulk_create(slots)
        return Response({'message': f'{count} slots created'}, status=status.HTTP_201_CREATED)


class CommercialParkingSlotViewSet(viewsets.ModelViewSet):
    queryset = CommercialParkingSlot.objects.all()
    serializer_class = CommercialParkingSlotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['facility', 'floor', 'slot_type', 'is_occupied', 'is_disabled']


class PrivateParkingListingViewSet(viewsets.ModelViewSet):
    queryset = PrivateParkingListing.objects.all()
    serializer_class = PrivateParkingListingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['has_cctv', 'is_covered', 'has_ev_charging', 'is_24_hours', 'auto_accept_bookings']
    search_fields = ['title', 'address', 'description']
    ordering_fields = ['hourly_rate', 'daily_rate', 'rating', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PrivateParkingListingListSerializer
        return PrivateParkingListingSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by owner if 'mine' param is present
        if self.request.query_params.get('mine') == 'true' and self.request.user.is_authenticated:
            return queryset.filter(owner=self.request.user)

        # Calculate distance if user location provided
        user_lat = self.request.query_params.get('lat')
        user_lon = self.request.query_params.get('lon')
        if user_lat and user_lon:
            listings_with_distance = []
            for listing in queryset:
                distance = calculate_distance(user_lat, user_lon, listing.latitude, listing.longitude)
                listing.distance = distance
                listings_with_distance.append(listing)
            
            # Sort by distance
            listings_with_distance.sort(key=lambda x: x.distance)
            return listings_with_distance
        
        return queryset

    @action(detail=True, methods=['post'])
    def pricing_intelligence(self, request, pk=None):
        return Response({
          "suggested_hourly_rate": "45.00",
          "current_rate": "40.00",
          "nearby_listings_count": 5,
          "avg_nearby_rate": "45.50",
          "min_nearby_rate": "35.00",
          "max_nearby_rate": "55.00"
        })


class PrivateParkingSlotViewSet(viewsets.ModelViewSet):
    queryset = PrivateParkingSlot.objects.all()
    serializer_class = PrivateParkingSlotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['listing', 'is_occupied', 'is_disabled']
