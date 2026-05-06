"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

const DEFAULT_CENTER = [41.3111, 69.2797];
const DEFAULT_ZOOM = 11;

export default function Home() {
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
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
      <main className={styles.main}>
        <div ref={mapElRef} className={styles.map} />
      </main>
    </div>
  );
}
