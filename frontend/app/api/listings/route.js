const listings = [
  {
    id: "demo-1",
    lat: 41.3111,
    lon: 69.2797,
    price: 420,
    address: "Amir Temur Avenue",
    district: "Yunusobod",
    status: "available",
  },
  {
    id: "demo-2",
    lat: 41.2922,
    lon: 69.2463,
    price: 560,
    address: "Buyuk Ipak Yoli",
    district: "Mirzo Ulugbek",
    status: "available",
  },
  {
    id: "demo-3",
    lat: 41.2701,
    lon: 69.2125,
    price: 390,
    address: "Chilonzor 9",
    district: "Chilonzor",
    status: "taken",
  },
];

export async function GET() {
  return Response.json(listings.filter((item) => item.status === "available"));
}
