import { Flow, GeohashGrid } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Proximity search" };

export default function Search() {
  return (
    <>
      <DocHeader
        eyebrow="Core flows"
        title="Proximity search"
        lead="“Show me parking within 5 km” is the most frequent request we serve. PostGIS answers it exactly; a geohash-cell cache lets drivers who are near each other share one cached answer."
      />

      <H2 id="query">The query</H2>
      <P>
        Each listing stores its position as a PostGIS <Code>geography</Code> point with a GiST index, so a radius search is
        an index scan, not a scan of every listing. Results carry the distance, price, rating and how many slots are free
        for the requested window.
      </P>
      <CodeBlock
        lang="http"
        title="request"
        code={`GET /v1/listings?latitude=12.9716&longitude=77.5946&radius_km=5&amenities=ev&sort=distance

# radius defaults to 5 km, at most 25 km; up to 200 results`}
      />

      <H2 id="cells">Sharing a cache between nearby drivers</H2>
      <P>
        Caching by exact coordinates is useless: no two phones send the same GPS fix. We cache by geohash cell instead.
        The cell query covers the requested radius plus the cell&apos;s half-diagonal, so it contains every listing any
        driver in that cell could see. Each request then filters and re-measures the cached candidates against its own
        position, so answers stay exact.
      </P>
      <Figure caption="Drivers A and B stand in the same cell, so both are served from one cached query (dashed circle). Each still gets exactly the listings inside their own radius.">
        <GeohashGrid />
      </Figure>
      <CodeBlock
        lang="python"
        title="app/domain/geo.py"
        code={`def cell_for_search(latitude, longitude, radius_m, max_error_ratio) -> Cell:
    """Coarsest cell whose half-diagonal is at most max_error_ratio of the radius
    (coarser cells = more cache sharing; the extra area is filtered out per request)."""
    for precision in range(1, 10):
        cell = decode_cell(encode(latitude, longitude, precision))
        if cell.half_diagonal_m <= radius_m * max_error_ratio:
            return cell
    return decode_cell(encode(latitude, longitude, 9))`}
      />

      <H2 id="flow">Request flow</H2>
      <Figure caption="Search reads from a read-only session, which can point at a read replica when one is configured." wide={false}>
        <Flow
          steps={[
            { title: "Pick the cell", tag: "geo.py", detail: "Coarsest geohash cell whose half-diagonal is at most 25% of the radius." },
            {
              branches: [
                { title: "Cache hit", tone: "success", tag: "Redis", detail: "Candidates for the cell, cached for 30 seconds." },
                { title: "Cache miss", tone: "accent", tag: "PostGIS", detail: "One indexed radius query for radius + half-diagonal, then stored." },
              ],
            },
            { title: "Filter for this driver", detail: "Re-measure distance from the driver's exact position, drop anything outside the radius, apply amenities, price and availability filters." },
            { title: "Sort and respond", detail: "By distance or price, with free-slot counts for the requested window." },
          ]}
        />
      </Figure>

      <H2 id="freshness">Keeping results fresh</H2>
      <DataTable
        head={["Event", "What happens to the cache"]}
        rows={[
          ["Listing created, edited, paused or deleted", "The search namespace version is bumped (one Redis INCR); every older key becomes unreachable and expires on its own"],
          ["Time passes", "Entries expire after 30 seconds, which bounds how stale availability can be"],
          ["Redis unavailable", "Search falls through to PostGIS, slower but still correct"],
        ]}
      />
      <Callout title="Measured" tone="success">
        Search sustained <b>865 requests per second</b> on 4 workers in our load test. It is our busiest read, and it
        was the first endpoint to hit database connection limits, which is why it has both the cell cache and a fast
        503 when the pool is exhausted.
      </Callout>

      <PrevNext slug="search" />
    </>
  );
}
