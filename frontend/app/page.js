"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

const DEFAULT_CENTER = [41.3111, 69.2797];
const DEFAULT_ZOOM = 11;

const METRO_LINES = [
  {
    id: "chilonzor",
    name: "Chilonzor",
    color: "#d64541",
    stations: [
      { name: "Olmazor", coords: [41.2915, 69.2016] },
      { name: "Chilonzor", coords: [41.2891, 69.2098] },
      { name: "Novza", coords: [41.2993, 69.2209] },
      { name: "Milliy Bog", coords: [41.3052, 69.2333] },
      { name: "Bunyodkor", coords: [41.3097, 69.2522] },
      { name: "Pakhtakor", coords: [41.3158, 69.2663] },
      { name: "Mustaqillik Maydoni", coords: [41.3179, 69.281] },
      { name: "Amir Temur Hiyoboni", coords: [41.3224, 69.2834] },
    ],
  },
  {
    id: "uzbekiston",
    name: "Uzbekiston",
    color: "#2d72d9",
    stations: [
      { name: "Beruniy", coords: [41.3276, 69.1678] },
      { name: "Tinchlik", coords: [41.331, 69.2035] },
      { name: "Chorsu", coords: [41.3247, 69.2423] },
      { name: "Gafur Gulom", coords: [41.3194, 69.2654] },
      { name: "Alisher Navoi", coords: [41.3156, 69.2689] },
      { name: "Kosmonavtlar", coords: [41.3119, 69.2826] },
      { name: "Oybek", coords: [41.3065, 69.2908] },
      { name: "Toshkent", coords: [41.2997, 69.2767] },
      { name: "Mashinasozlar", coords: [41.2763, 69.3096] },
      { name: "Do'stlik", coords: [41.2695, 69.3272] },
    ],
  },
  {
    id: "yunusobod",
    name: "Yunusobod",
    color: "#2e8b57",
    stations: [
      { name: "Shahriston", coords: [41.3602, 69.2876] },
      { name: "Bodomzor", coords: [41.3482, 69.2855] },
      { name: "Minor", coords: [41.337, 69.2853] },
      { name: "Abdulla Qodiriy", coords: [41.329, 69.286] },
      { name: "Yunus Rajabiy", coords: [41.3208, 69.2837] },
      { name: "Ming Orik", coords: [41.312, 69.294] },
      { name: "Oybek", coords: [41.3065, 69.2908] },
    ],
  },
];

export default function Home() {
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const webApp = window?.Telegram?.WebApp;
    const mapContainer = mapElRef.current;
    const stopTouchBubble = (event) => {
      event.stopPropagation();
    };

    if (webApp?.disableVerticalSwipes) {
      webApp.disableVerticalSwipes();
    }
    webApp?.ready?.();
    webApp?.expand?.();

    if (mapContainer) {
      mapContainer.addEventListener("touchstart", stopTouchBubble, {
        passive: true,
      });
      mapContainer.addEventListener("touchmove", stopTouchBubble, {
        passive: true,
      });
    }

    let isMounted = true;

    const initMap = async () => {
      if (!mapElRef.current || mapRef.current) {
        return;
      }

      const leafletModule = await import("leaflet");
      const L = leafletModule.default ?? leafletModule;

      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl:
          "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl:
          "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const mapInstance = L.map(mapElRef.current, {
        zoomControl: false,
        preferCanvas: true,
      }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

      L.control.zoom({ position: "bottomright" }).addTo(mapInstance);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(mapInstance);

      const metroPane = mapInstance.createPane("metro");
      metroPane.style.zIndex = 450;

      const metroLayer = L.layerGroup().addTo(mapInstance);
      METRO_LINES.forEach((line) => {
        const coords = line.stations.map((station) => station.coords);
        L.polyline(coords, {
          color: line.color,
          weight: 4,
          opacity: 0.9,
          pane: "metro",
        }).addTo(metroLayer);

        line.stations.forEach((station) => {
          L.circleMarker(station.coords, {
            radius: 4,
            weight: 1,
            color: "#ffffff",
            fillColor: line.color,
            fillOpacity: 1,
            pane: "metro",
          })
            .addTo(metroLayer)
            .bindTooltip(station.name, {
              className: styles.metroTooltip,
              direction: "top",
              offset: [0, -6],
              opacity: 0.9,
            });
        });
      });

      const markersLayer = L.layerGroup().addTo(mapInstance);
      mapRef.current = mapInstance;

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE;
        const apiKey = process.env.NEXT_PUBLIC_API_KEY;
        const endpoint = apiBase
          ? `${apiBase.replace(/\/$/, "")}/api/listings`
          : "/api/listings";

        const headers = {
          "ngrok-skip-browser-warning": "true",
        };
        if (apiKey) {
          headers["x-api-key"] = apiKey;
        }

        const response = await fetch(endpoint, { headers });
        if (!response.ok) {
          throw new Error("Failed to load listings");
        }
        const data = await response.json();

        if (!isMounted) {
          return;
        }

        setCount(data.length);
        if (data.length === 0) {
          return;
        }

        const bounds = [];
        data.forEach((item) => {
          if (!item.lat || !item.lon) {
            return;
          }

          const priceLabel =
            typeof item.price === "number"
              ? `${item.price.toLocaleString("en-US")} $`
              : "Narx kelishiladi";

          const priceIcon = L.divIcon({
            className: styles.pricePin,
            html: `<div class="${styles.pricePinLabel}">${priceLabel}</div>`,
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          });

          L.marker([item.lat, item.lon], { icon: priceIcon }).addTo(
            markersLayer,
          );
          bounds.push([item.lat, item.lon]);
        });

        if (bounds.length > 0) {
          mapInstance.fitBounds(bounds, { padding: [30, 30] });
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setCount(0);
      }
    };

    initMap();

    return () => {
      isMounted = false;
      if (mapContainer) {
        mapContainer.removeEventListener("touchstart", stopTouchBubble);
        mapContainer.removeEventListener("touchmove", stopTouchBubble);
      }
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.glow} aria-hidden />
      <div className={styles.floatingBadge}>E'lonlar: {count}</div>
      <div className={styles.metroLegend}>
        <div className={styles.metroLegendTitle}>Tashkent metro</div>
        {METRO_LINES.map((line) => (
          <div key={line.id} className={styles.metroLegendRow}>
            <span
              className={styles.metroLegendSwatch}
              style={{ backgroundColor: line.color }}
            />
            <span className={styles.metroLegendLabel}>{line.name}</span>
          </div>
        ))}
      </div>
      <main className={styles.main}>
        <div ref={mapElRef} className={styles.map} />
      </main>
    </div>
  );
}
