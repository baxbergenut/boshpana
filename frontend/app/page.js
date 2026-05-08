"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./page.module.css";

const DEFAULT_CENTER = [41.3111, 69.2797];
const DEFAULT_ZOOM = 11;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const METRO_COLOR_MAP = {
  red: { label: "Red line", color: "#d64541" },
  blue: { label: "Blue line", color: "#2d72d9" },
  green: { label: "Green line", color: "#2e8b57" },
};

const getMetroColor = (rawColor) => {
  if (!rawColor) {
    return "#5b5b5b";
  }

  if (rawColor.startsWith("#")) {
    return rawColor;
  }

  return METRO_COLOR_MAP[rawColor]?.color ?? "#5b5b5b";
};

const buildLegendItems = (geojson) => {
  const seen = new Set();
  const items = [];

  geojson?.features?.forEach((feature) => {
    const rawColor = feature?.properties?.colour;
    if (!rawColor || seen.has(rawColor)) {
      return;
    }

    seen.add(rawColor);
    items.push({
      key: rawColor,
      label: METRO_COLOR_MAP[rawColor]?.label ?? rawColor,
      color: getMetroColor(rawColor),
    });
  });

  return items;
};

const buildFallbackLines = (geojson) => {
  const hasLinework = geojson?.features?.some((feature) => {
    const type = feature?.geometry?.type;
    return type && type !== "Point" && type !== "MultiPoint";
  });

  if (hasLinework) {
    return [];
  }

  const groups = new Map();
  geojson?.features?.forEach((feature) => {
    const type = feature?.geometry?.type;
    if (type !== "Point") {
      return;
    }

    const rawColor = feature?.properties?.colour ?? "unknown";
    const coords = feature?.geometry?.coordinates;
    if (!Array.isArray(coords) || coords.length < 2) {
      return;
    }

    const entry = {
      latlng: [coords[1], coords[0]],
      color: getMetroColor(rawColor),
      rawColor,
    };

    if (!groups.has(rawColor)) {
      groups.set(rawColor, []);
    }
    groups.get(rawColor).push(entry);
  });

  const lines = [];

  groups.forEach((stations, rawColor) => {
    if (stations.length < 2) {
      return;
    }

    const remaining = [...stations];
    remaining.sort((a, b) => {
      if (a.latlng[1] !== b.latlng[1]) {
        return a.latlng[1] - b.latlng[1];
      }
      return a.latlng[0] - b.latlng[0];
    });

    const ordered = [remaining.shift()];
    while (remaining.length > 0) {
      const current = ordered[ordered.length - 1];
      let nearestIndex = 0;
      let nearestDistance = Infinity;

      remaining.forEach((candidate, index) => {
        const dx = candidate.latlng[0] - current.latlng[0];
        const dy = candidate.latlng[1] - current.latlng[1];
        const distance = dx * dx + dy * dy;
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nearestIndex = index;
        }
      });

      ordered.push(remaining.splice(nearestIndex, 1)[0]);
    }

    lines.push({
      color: getMetroColor(rawColor),
      coords: ordered.map((station) => station.latlng),
    });
  });

  return lines;
};

const buildApiEndpoint = (path) => {
  if (!API_BASE) {
    return path;
  }

  return `${API_BASE.replace(/\/$/, "")}${path}`;
};

const buildApiHeaders = () => {
  const headers = {
    "ngrok-skip-browser-warning": "true",
  };

  if (API_KEY) {
    headers["x-api-key"] = API_KEY;
  }

  return headers;
};

const AMENITY_LABELS = {
  has_wifi: "WiFi",
  has_washing_machine: "Kir yuvish mashina",
  has_fridge: "Muzlatgich",
  has_ac: "Konditsioner",
  has_heating: "Isitish",
  has_parking: "Parking",
  has_elevator: "Lift",
  has_furniture: "Mebel",
};

const TENANT_PREF_LABELS = {
  for_boys: "Yigitlar",
  for_girls: "Qizlar",
  for_families: "Oila",
};

const formatPrice = (price, currency, perPerson) => {
  if (!price || typeof price !== "number") {
    return "Narx kelishiladi";
  }

  const formatted = `${price.toLocaleString("en-US")} ${currency || "USD"}`;
  return perPerson ? `${formatted} (odam boshiga)` : formatted;
};

const formatValue = (value, fallback = "-") => {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
};

const sanitizePhone = (phone) => {
  if (!phone) {
    return "";
  }

  return phone.replace(/[^+0-9]/g, "");
};

const buildTelegramLink = (username) => {
  if (!username) {
    return "";
  }

  const clean = username.startsWith("@") ? username.slice(1) : username;
  return clean ? `https://t.me/${clean}` : "";
};

export default function Home() {
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const [count, setCount] = useState(0);
  const [metroData, setMetroData] = useState(null);
  const [selectedListing, setSelectedListing] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");
  const metroLegendItems = useMemo(
    () => buildLegendItems(metroData),
    [metroData],
  );

  const isDetailsOpen = Boolean(
    selectedListing || detailsLoading || detailsError,
  );

  const loadListingDetails = async (listingId) => {
    if (!listingId) {
      return;
    }

    setDetailsLoading(true);
    setDetailsError("");
    setSelectedListing(null);

    try {
      const response = await fetch(
        buildApiEndpoint(`/api/listings/${listingId}`),
        { headers: buildApiHeaders() },
      );
      if (!response.ok) {
        throw new Error("Failed to load listing detail");
      }

      const payload = await response.json();
      setSelectedListing(payload);
    } catch (error) {
      setDetailsError("Tafsilotlarni yuklab bo'lmadi. Qayta urinib ko'ring.");
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleCloseDetails = () => {
    setSelectedListing(null);
    setDetailsError("");
    setDetailsLoading(false);
  };

  useEffect(() => {
    const webApp = window?.Telegram?.WebApp;

    webApp?.ready?.();
    webApp?.expand?.();

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

      try {
        const metroResponse = await fetch("/tashkent-metro.geojson");
        if (metroResponse.ok) {
          const geojson = await metroResponse.json();
          if (isMounted) {
            setMetroData(geojson);
          }

          L.geoJSON(geojson, {
            pane: "metro",
            style: (feature) => ({
              color: getMetroColor(feature?.properties?.colour),
              weight: 4,
              opacity: 0.9,
            }),
            pointToLayer: (feature, latlng) =>
              L.circleMarker(latlng, {
                radius: 4,
                weight: 1,
                color: "#ffffff",
                fillColor: getMetroColor(feature?.properties?.colour),
                fillOpacity: 1,
                pane: "metro",
              }),
            onEachFeature: (feature, layer) => {
              const name = feature?.properties?.name;
              if (!name) {
                return;
              }

              layer.bindTooltip(name, {
                className: styles.metroTooltip,
                direction: "top",
                offset: [0, -6],
                opacity: 0.9,
              });
            },
          }).addTo(mapInstance);

          buildFallbackLines(geojson).forEach((line) => {
            L.polyline(line.coords, {
              color: line.color,
              weight: 4,
              opacity: 0.85,
              pane: "metro",
            }).addTo(mapInstance);
          });
        }
      } catch (error) {
        // Skip metro overlay if the GeoJSON fails to load.
      }

      const markersLayer = L.layerGroup().addTo(mapInstance);
      mapRef.current = mapInstance;

      try {
        const response = await fetch(buildApiEndpoint("/api/listings"), {
          headers: buildApiHeaders(),
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

          const marker = L.marker([item.lat, item.lon], { icon: priceIcon });
          marker.on("click", () => loadListingDetails(item.id));
          marker.addTo(markersLayer);
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
      {metroLegendItems.length > 0 && (
        <div className={styles.metroLegend}>
          <div className={styles.metroLegendTitle}>Tashkent metro</div>
          {metroLegendItems.map((item) => (
            <div key={item.key} className={styles.metroLegendRow}>
              <span
                className={styles.metroLegendSwatch}
                style={{ backgroundColor: item.color }}
              />
              <span className={styles.metroLegendLabel}>{item.label}</span>
            </div>
          ))}
        </div>
      )}
      <main className={styles.main}>
        <div ref={mapElRef} className={styles.map} />
      </main>
      <section
        className={`${styles.detailPanel} ${
          isDetailsOpen ? styles.detailPanelActive : ""
        }`}
        aria-live="polite"
      >
        <div className={styles.detailHeader}>
          <div className={styles.detailHeaderInfo}>
            <div className={styles.detailTitle}>
              {selectedListing
                ? formatPrice(
                    selectedListing.price,
                    selectedListing.currency,
                    selectedListing.price_per_person,
                  )
                : detailsLoading
                  ? "Yuklanmoqda..."
                  : "Tafsilotlar"}
            </div>
            {selectedListing && (
              <div className={styles.detailSubtitle}>
                {formatValue(selectedListing.address)}
              </div>
            )}
          </div>
          <div className={styles.detailHeaderActions}>
            {selectedListing && (
              <div className={styles.detailActionButtons}>
                {selectedListing.owner_phone && (
                  <a
                    className={styles.detailActionButton}
                    href={`tel:${sanitizePhone(selectedListing.owner_phone)}`}
                  >
                    Call
                  </a>
                )}
                {selectedListing.owner_username && (
                  <a
                    className={`${styles.detailActionButton} ${styles.detailActionButtonGhost}`}
                    href={buildTelegramLink(selectedListing.owner_username)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Telegram
                  </a>
                )}
              </div>
            )}
            <button
              type="button"
              className={styles.detailClose}
              onClick={handleCloseDetails}
              aria-label="Close details"
            >
              x
            </button>
          </div>
        </div>
        <div className={styles.detailBody}>
          {detailsError && (
            <div className={styles.detailError}>{detailsError}</div>
          )}
          {detailsLoading && (
            <div className={styles.detailLoading}>Yuklanmoqda...</div>
          )}
          {selectedListing && (
            <>
              <div className={styles.detailSectionTitle}>Rasmlar</div>
              {selectedListing.photos?.length ? (
                <div className={styles.photoStrip}>
                  {selectedListing.photos.map((photo, index) => (
                    <div key={photo.id || index} className={styles.photoFrame}>
                      {photo.url ? (
                        <img
                          src={photo.url}
                          alt="Listing"
                          className={styles.photo}
                          loading="lazy"
                        />
                      ) : (
                        <div className={styles.photoFallback}>Rasm</div>
                      )}
                      <div className={styles.photoIndex}>
                        {index + 1}/{selectedListing.photos.length}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.photoEmpty}>Rasm topilmadi.</div>
              )}

              <div className={styles.detailSectionTitle}>Asosiy ma'lumot</div>
              <div className={styles.detailGrid}>
                <div>
                  <div className={styles.detailLabel}>Xonalar</div>
                  <div className={styles.detailValue}>
                    {formatValue(selectedListing.rooms)}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Qavat</div>
                  <div className={styles.detailValue}>
                    {formatValue(
                      selectedListing.floor !== null &&
                        selectedListing.total_floors !== null
                        ? `${selectedListing.floor}/${selectedListing.total_floors}`
                        : selectedListing.floor,
                    )}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Maydon</div>
                  <div className={styles.detailValue}>
                    {selectedListing.area_sqm
                      ? `${selectedListing.area_sqm} kv.m`
                      : "-"}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Tuman</div>
                  <div className={styles.detailValue}>
                    {formatValue(selectedListing.district)}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Sheriklik</div>
                  <div className={styles.detailValue}>
                    {selectedListing.shared ? "Ha" : "Yo'q"}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Kelishuv</div>
                  <div className={styles.detailValue}>
                    {selectedListing.price_negotiable ? "Ha" : "Yo'q"}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Maks. ijarachi</div>
                  <div className={styles.detailValue}>
                    {formatValue(selectedListing.max_tenants)}
                  </div>
                </div>
                <div>
                  <div className={styles.detailLabel}>Kerakli ijarachi</div>
                  <div className={styles.detailValue}>
                    {formatValue(selectedListing.needed_tenants)}
                  </div>
                </div>
              </div>

              <div className={styles.detailSectionTitle}>Qulayliklar</div>
              <div className={styles.detailValueBlock}>
                {(selectedListing.amenities || []).length
                  ? selectedListing.amenities
                      .map((key) => AMENITY_LABELS[key] || key)
                      .join(", ")
                  : "Yo'q"}
              </div>

              <div className={styles.detailSectionTitle}>Kimlarga mos</div>
              <div className={styles.detailValueBlock}>
                {(selectedListing.tenant_prefs || []).length
                  ? selectedListing.tenant_prefs
                      .map((key) => TENANT_PREF_LABELS[key] || key)
                      .join(", ")
                  : "Cheklov yo'q"}
              </div>

              <div className={styles.detailSectionTitle}>Kommunal</div>
              <div className={styles.detailValueBlock}>
                {selectedListing.utils_included
                  ? "Kommunal to'lovlar kiritilgan"
                  : "Kommunal alohida"}
              </div>

              <div className={styles.detailSectionTitle}>Tavsif</div>
              <div className={styles.detailValueBlock}>
                {formatValue(selectedListing.description, "Yo'q")}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
