import { createElement, forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import type { ListingSearchItem } from '@/api/types';
import { useTheme } from '@/ui/theme';

export type MapRegion = { latitude: number; longitude: number; latitudeDelta: number; longitudeDelta: number };
export type ParkingMapHandle = { animateTo: (region: MapRegion) => void };

type Props = {
  initialRegion: MapRegion;
  items: ListingSearchItem[];
  showsUserLocation: boolean;
  userLocation?: { latitude: number; longitude: number; heading?: number } | null;
  /** Radius in metres of the "near you" zone drawn around the user's location. */
  zoneRadiusM?: number;
  onRegionChange: (region: MapRegion) => void;
  onSelect: (item: ListingSearchItem) => void;
};

/** Web implementation of OpenStreetMap using Leaflet and official OSM tiles. */
export const ParkingMap = forwardRef<ParkingMapHandle, Props>(function ParkingMap(
  { initialRegion, items, userLocation, zoneRadiusM, onRegionChange, onSelect },
  ref,
) {
  const { colors } = useTheme();
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const itemsRef = useRef(items);
  const onSelectRef = useRef(onSelect);
  const onRegionChangeRef = useRef(onRegionChange);
  const userLocationRef = useRef(userLocation);
  const zoneRef = useRef(zoneRadiusM);

  useEffect(() => {
    itemsRef.current = items;
    onSelectRef.current = onSelect;
    onRegionChangeRef.current = onRegionChange;
    userLocationRef.current = userLocation;
    zoneRef.current = zoneRadiusM;
  }, [items, onSelect, onRegionChange, userLocation, zoneRadiusM]);

  const postUser = () => {
    const u = userLocationRef.current;
    if (!u) return;
    iframeRef.current?.contentWindow?.postMessage(
      {
        source: 'parkezy-host',
        type: 'SET_USER_LOCATION',
        lat: u.latitude,
        lng: u.longitude,
        heading: u.heading ?? 0,
        zone: zoneRef.current ?? 0,
      },
      '*',
    );
  };

  useImperativeHandle(ref, () => ({
    animateTo: (region) => {
      iframeRef.current?.contentWindow?.postMessage(
        { source: 'parkezy-host', type: 'SET_CENTER', lat: region.latitude, lng: region.longitude },
        '*',
      );
    },
  }));

  // Sync user location (and the zone around it) to the iframe
  useEffect(() => {
    if (userLocation) postUser();
  }, [userLocation?.latitude, userLocation?.longitude, userLocation?.heading, zoneRadiusM]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle messages from the iframe (marker clicks, map pans)
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.source !== 'parkezy-osm') return;
      if (e.data.type === 'SELECT_ITEM') {
        const item = itemsRef.current.find((x) => x.id === e.data.id);
        if (item) onSelectRef.current(item);
      } else if (e.data.type === 'REGION_CHANGE') {
        onRegionChangeRef.current({
          latitude: e.data.latitude,
          longitude: e.data.longitude,
          latitudeDelta: e.data.latitudeDelta || 0.05,
          longitudeDelta: e.data.longitudeDelta || 0.05,
        });
      } else if (e.data.type === 'READY') {
        // Send initial items when iframe reports ready
        const payload = itemsRef.current.map((x) => ({
          id: x.id,
          lat: x.latitude,
          lng: x.longitude,
          price: Math.round(Number(x.hourly_rate)),
          title: x.title,
          full: x.available_slots === 0,
        }));
        iframeRef.current?.contentWindow?.postMessage({ source: 'parkezy-host', type: 'UPDATE_ITEMS', items: payload }, '*');
        postUser();
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // Sync items to iframe whenever items change
  useEffect(() => {
    const payload = items.map((x) => ({
      id: x.id,
      lat: x.latitude,
      lng: x.longitude,
      price: Math.round(Number(x.hourly_rate)),
      title: x.title,
      full: x.available_slots === 0,
    }));
    iframeRef.current?.contentWindow?.postMessage({ source: 'parkezy-host', type: 'UPDATE_ITEMS', items: payload }, '*');
  }, [items]);

  // Built ONCE from the first region. Rebuilding it on every pan/zoom changed the iframe's srcDoc,
  // which reloaded the whole map and snapped it back. Later moves are sent with postMessage.
  const [leafletHtml] = useState(() => `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #ffffff; }
    .price-pin {
      background: #6E5BC4;
      color: #ffffff;
      font-weight: 800;
      font-size: 13px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 6px 12px;
      border-radius: 999px;
      box-shadow: 0 4px 14px rgba(110, 91, 196, 0.4);
      white-space: nowrap;
      cursor: pointer;
      display: inline-block;
      text-align: center;
      transition: transform 0.15s ease;
    }
    .price-pin:hover {
      transform: scale(1.1);
    }
    .price-pin.full {
      background: #F2F0F7;
      color: #666173;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .user-arrow-beacon {
      position: relative;
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .user-arrow-pulse {
      position: absolute;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(110, 91, 196, 0.22);
      border: 2px solid #6E5BC4;
    }
    .user-arrow-disc {
      position: relative;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #6E5BC4;
      border: 2.5px solid #ffffff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s ease;
    }
    .user-arrow-disc svg {
      width: 16px;
      height: 16px;
      fill: #ffffff;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', { zoomControl: false }).setView([${initialRegion.latitude}, ${initialRegion.longitude}], 14);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var markersLayer = L.layerGroup().addTo(map);
    var userMarker = null;
    var zoneCircle = null;
    var centeredOnUser = false;

    function renderUser(lat, lng, heading, zone) {
      if (zone > 0) {
        if (!zoneCircle) {
          zoneCircle = L.circle([lat, lng], {
            radius: zone, color: '#6E5BC4', weight: 1.5, fillColor: '#6E5BC4', fillOpacity: 0.1, interactive: false
          }).addTo(map);
        } else {
          zoneCircle.setLatLng([lat, lng]);
          zoneCircle.setRadius(zone);
        }
      }
      if (!userMarker) {
        var icon = L.divIcon({
          className: '',
          html: '<div class="user-arrow-beacon"><div class="user-arrow-pulse"></div><div class="user-arrow-disc"><svg viewBox="0 0 512 512"><path d="M256 40L88 472l168-96 168 96z"/></svg></div></div>',
          iconSize: [44, 44],
          iconAnchor: [22, 22]
        });
        userMarker = L.marker([lat, lng], { icon: icon, zIndexOffset: 1000, interactive: false }).addTo(map);
      } else {
        userMarker.setLatLng([lat, lng]);
      }
      var disc = userMarker.getElement() && userMarker.getElement().querySelector('.user-arrow-disc');
      if (disc) disc.style.transform = 'rotate(' + (heading || 0) + 'deg)';
      // First fix: bring the user and their zone into view.
      if (!centeredOnUser) {
        centeredOnUser = true;
        map.setView([lat, lng], Math.max(map.getZoom(), 14));
      }
    }

    // Pins are kept by id and only added/removed when results change, so nothing flickers while panning.
    var pins = {};
    function renderMarkers(items) {
      items = items || [];
      var next = {};
      items.forEach(function(item) {
        var sig = item.lat + ',' + item.lng + ',' + item.price + ',' + item.full;
        var existing = pins[item.id];
        if (existing && existing.sig === sig) {
          next[item.id] = existing;
          delete pins[item.id];
          return;
        }
        var icon = L.divIcon({
          className: '',
          html: '<div class="price-pin ' + (item.full ? 'full' : '') + '">₹' + item.price + '</div>',
          iconSize: [60, 30],
          iconAnchor: [30, 15]
        });
        var marker = L.marker([item.lat, item.lng], { icon: icon });
        marker.on('click', function() {
          window.parent.postMessage({ source: 'parkezy-osm', type: 'SELECT_ITEM', id: item.id }, '*');
        });
        markersLayer.addLayer(marker);
        next[item.id] = { marker: marker, sig: sig };
      });
      Object.keys(pins).forEach(function(id) { markersLayer.removeLayer(pins[id].marker); });
      pins = next;
    }

    var debounceTimer;
    map.on('moveend', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function() {
        var center = map.getCenter();
        var bounds = map.getBounds();
        window.parent.postMessage({
          source: 'parkezy-osm',
          type: 'REGION_CHANGE',
          latitude: center.lat,
          longitude: center.lng,
          latitudeDelta: Math.abs(bounds.getNorth() - bounds.getSouth()),
          longitudeDelta: Math.abs(bounds.getEast() - bounds.getWest())
        }, '*');
      }, 350);
    });

    window.addEventListener('message', function(e) {
      if (!e.data || e.data.source !== 'parkezy-host') return;
      if (e.data.type === 'UPDATE_ITEMS') {
        renderMarkers(e.data.items);
      } else if (e.data.type === 'SET_CENTER') {
        map.setView([e.data.lat, e.data.lng], map.getZoom(), { animate: true });
      } else if (e.data.type === 'SET_USER_LOCATION') {
        renderUser(e.data.lat, e.data.lng, e.data.heading, e.data.zone);
      }
    });

    // Notify parent ready
    setTimeout(function() {
      window.parent.postMessage({ source: 'parkezy-osm', type: 'READY' }, '*');
    }, 100);
  </script>
</body>
</html>`);

  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.canvas }]}>
      {createElement('iframe', {
        ref: iframeRef,
        srcDoc: leafletHtml,
        style: { width: '100%', height: '100%', border: 'none' },
        title: 'OpenStreetMap Web View',
      })}
    </View>
  );
});
