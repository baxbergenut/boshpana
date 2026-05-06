"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

const DEFAULT_CENTER = [41.3111, 69.2797];
const DEFAULT_ZOOM = 11;

export default function Home() {
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const [count, setCount] = useState(0);
  const [status, setStatus] = useState("Loading listings...");

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

        const response = await fetch(endpoint, {
          headers: apiKey ? { "x-api-key": apiKey } : {},
        });
        if (!response.ok) {
          throw new Error("Failed to load listings");
        }
        const data = await response.json();

        if (!isMounted) {
          return;
        }

        setCount(data.length);
        if (data.length === 0) {
          setStatus("No listings yet.");
          return;
        }

        const bounds = [];
        data.forEach((item) => {
          if (!item.lat || !item.lon) {
            return;
          }

          const price =
            typeof item.price === "number"
              ? `$${item.price.toLocaleString("en-US")}`
              : "Price on request";
          const address = item.address || item.district || "Address hidden";

          const marker = L.marker([item.lat, item.lon]).addTo(markersLayer);
          marker.bindPopup(`<strong>${price}</strong><br/>${address}`);
          bounds.push([item.lat, item.lon]);
        });

        if (bounds.length > 0) {
          mapInstance.fitBounds(bounds, { padding: [30, 30] });
          setStatus("Tap a pin for details.");
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setStatus("Could not load listings.");
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
      <header className={styles.panel}>
        <span className={styles.badge}>Live map</span>
        <h1>Boshpana listings map</h1>
        <p>
          A live view of every available apartment. Tap a pin to see price and
          area.
        </p>
        <div className={styles.stats}>
          <div>
            <span className={styles.label}>Listings</span>
            <span className={styles.value}>{count}</span>
          </div>
          <div>
            <span className={styles.label}>Status</span>
            <span className={styles.value}>{status}</span>
          </div>
        </div>
      </header>
      <main className={styles.main}>
        <div ref={mapElRef} className={styles.map} />
        <div className={styles.cornerCard}>
          <span className={styles.mono}>Tip</span>
          <p>Pin clusters will appear once you add more listings.</p>
        </div>
      </main>
    </div>
  );
}
