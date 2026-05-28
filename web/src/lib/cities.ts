/**
 * World city codename pool — used to encode exam names.
 * 100+ distinct, recognisable cities. We pick the first unused name
 * (in order) when publishing a new exam.
 */
export const CITY_POOL: string[] = [
  // Asia
  'Tokyo', 'Kyoto', 'Osaka', 'Seoul', 'Taipei',
  'Singapore', 'Bangkok', 'Bali', 'Jakarta', 'Manila',
  'Mumbai', 'Delhi', 'Dubai', 'Istanbul', 'Cairo',
  // Africa
  'Marrakech', 'Casablanca', 'Cape Town', 'Nairobi', 'Lagos',
  // Europe
  'Athens', 'Rome', 'Florence', 'Venice', 'Barcelona',
  'Madrid', 'Lisbon', 'Porto', 'Paris', 'Lyon',
  'Geneva', 'Zurich', 'Vienna', 'Prague', 'Berlin',
  'Munich', 'Amsterdam', 'Brussels', 'Copenhagen', 'Stockholm',
  'Oslo', 'Helsinki', 'Reykjavik', 'Dublin', 'London',
  'Edinburgh', 'Budapest', 'Warsaw', 'Krakow', 'Sofia',
  // Americas
  'Bucharest', 'Riga', 'Tallinn', 'Vilnius', 'Belgrade',
  'Zagreb', 'Ljubljana', 'Sarajevo', 'Skopje', 'Tirana',
  'New York', 'Boston', 'Chicago', 'Toronto', 'Vancouver',
  'Montreal', 'Quebec', 'Seattle', 'San Francisco', 'Los Angeles',
  'Austin', 'Miami', 'Mexico City', 'Oaxaca', 'Havana',
  'Bogota', 'Lima', 'Quito', 'Santiago', 'Buenos Aires',
  // Oceania + Other
  'Montevideo', 'Rio', 'Sao Paulo', 'Brasilia', 'Cartagena',
  'Sydney', 'Melbourne', 'Auckland', 'Wellington', 'Suva',
  'Honolulu', 'Tahiti', 'Beirut', 'Jerusalem', 'Petra',
  'Tehran', 'Baku', 'Tbilisi', 'Yerevan', 'Almaty',
  'Tashkent', 'Samarkand', 'Bukhara', 'Kathmandu', 'Colombo',
]

/**
 * Pick the first city in CITY_POOL that's not already used.
 * Returns undefined if pool is exhausted.
 */
export function pickNextCity(usedNames: Set<string>): string | undefined {
  for (const city of CITY_POOL) {
    if (!usedNames.has(city)) return city
  }
  return undefined
}
