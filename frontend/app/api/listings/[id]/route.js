const listings = {
  "demo-1": {
    id: "demo-1",
    status: "available",
    price: 420,
    currency: "USD",
    price_per_person: false,
    price_negotiable: true,
    rooms: 2,
    floor: 4,
    total_floors: 9,
    area_sqm: 54,
    district: "Yunusobod",
    address: "Amir Temur Avenue",
    lat: 41.3111,
    lon: 69.2797,
    shared: false,
    max_tenants: 2,
    needed_tenants: 0,
    utils_included: true,
    tenant_prefs: ["for_families"],
    amenities: ["has_wifi", "has_washing_machine", "has_furniture"],
    description: "Yorug' va toza xonadon. Metroga yaqin.",
    photos: [
      {
        id: "demo-1-1",
        url: "https://picsum.photos/seed/boshpana-1/800/600",
      },
      {
        id: "demo-1-2",
        url: "https://picsum.photos/seed/boshpana-2/800/600",
      },
    ],
  },
  "demo-2": {
    id: "demo-2",
    status: "available",
    price: 560,
    currency: "USD",
    price_per_person: false,
    price_negotiable: false,
    rooms: 3,
    floor: 2,
    total_floors: 5,
    area_sqm: 72,
    district: "Mirzo Ulugbek",
    address: "Buyuk Ipak Yoli",
    lat: 41.2922,
    lon: 69.2463,
    shared: false,
    max_tenants: 4,
    needed_tenants: 0,
    utils_included: false,
    tenant_prefs: ["for_boys", "for_girls"],
    amenities: ["has_wifi", "has_ac", "has_parking"],
    description: "Keng va qulay. Yaqin atrofda do'konlar bor.",
    photos: [
      {
        id: "demo-2-1",
        url: "https://picsum.photos/seed/boshpana-3/800/600",
      },
    ],
  },
  "demo-3": {
    id: "demo-3",
    status: "taken",
    price: 390,
    currency: "USD",
    price_per_person: true,
    price_negotiable: true,
    rooms: 1,
    floor: 7,
    total_floors: 9,
    area_sqm: 38,
    district: "Chilonzor",
    address: "Chilonzor 9",
    lat: 41.2701,
    lon: 69.2125,
    shared: true,
    max_tenants: 3,
    needed_tenants: 1,
    utils_included: true,
    tenant_prefs: ["for_boys"],
    amenities: ["has_washing_machine", "has_heating"],
    description: "Sheriklik uchun mos, sokin hudud.",
    photos: [],
  },
};

export async function GET(request, { params }) {
  const item = listings[params.id];
  if (!item || item.status !== "available") {
    return new Response(JSON.stringify({ error: "Listing not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  return Response.json(item);
}
