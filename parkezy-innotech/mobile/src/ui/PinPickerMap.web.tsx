import { createElement, useEffect, useRef } from 'react';
import { StyleSheet, View } from 'react-native';

import { env } from '@/config/env';
import type { MapRegion } from '@/ui/ParkingMap';
import { useTheme } from '@/ui/theme';

type Coords = { latitude: number; longitude: number };

/** Web implementation of OpenStreetMap pin picker. */
export function PinPickerMap({
  initialRegion,
  pin,
  onMove,
}: {
  initialRegion: MapRegion;
  pin: Coords | null;
  onMove: (c: Coords) => void;
}) {
  const { colors } = useTheme();
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const onMoveRef = useRef(onMove);
  useEffect(() => {
    onMoveRef.current = onMove;
  }, [onMove]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.source !== 'parkezy-pin') return;
      if (e.data.type === 'PIN_MOVED') {
        onMoveRef.current({ latitude: e.data.lat, longitude: e.data.lng });
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const lat = pin?.latitude ?? initialRegion.latitude;
  const lng = pin?.longitude ?? initialRegion.longitude;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #ffffff; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', { zoomControl: false }).setView([${lat}, ${lng}], 15);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.tileLayer('${env.osmTileUrl}', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var marker = L.marker([${lat}, ${lng}], { draggable: true }).addTo(map);

    function report(latlng) {
      window.parent.postMessage({
        source: 'parkezy-pin',
        type: 'PIN_MOVED',
        lat: latlng.lat,
        lng: latlng.lng
      }, '*');
    }

    marker.on('dragend', function(e) {
      report(marker.getLatLng());
    });

    map.on('click', function(e) {
      marker.setLatLng(e.latlng);
      report(e.latlng);
    });
  </script>
</body>
</html>`;

  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.canvas }]}>
      {createElement('iframe', {
        ref: iframeRef,
        srcDoc: html,
        style: { width: '100%', height: '100%', border: 'none' },
        title: 'Pin Picker OpenStreetMap',
      })}
    </View>
  );
}
