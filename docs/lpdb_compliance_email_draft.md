Subject: fandomdatapuller — LPDB access, compliance steps taken and in progress

Hi [LPDB contact name],

Thank you again for approving API access. Following up, as requested, now
that we're live and pulling real data — here's what we've done to make
sure we're using the API correctly and crediting Liquipedia properly, plus
two open questions we'd like to confirm with you directly.

**Project link**: https://github.com/JacobH1994/fandomdatapuller — public,
open source (MIT for our own code), as you asked.

**API usage, not scraping**

We're using the documented v3 REST API directly (`Authorization: Apikey`
header, `wiki` parameter, structured SQL-like `conditions` queries) —
never crawling or scraping Liquipedia pages. A descriptive `User-Agent`
identifying the project and this contact email is sent on every request.

We've been deliberately conservative on rate: your documented limit is 60
requests/hour, and our collector enforces that as a hard ceiling — tracked
across every run (not just a single process), persisted so it survives
restarts, with each individual run capped further below the real limit to
leave headroom rather than constantly running at the edge. We check this
budget before every batch of work rather than assuming it's safe.

**Attribution**

- Liquipedia-derived data in our repo (`data/reference/*.jsonl`) carries
  its own `README.md` crediting Liquipedia by name, linking to
  liquipedia.net and your Copyrights page, and stating the CC BY-SA
  license explicitly — kept separate from our own MIT-licensed code, not
  blended into one blanket license.
- Every external-facing report we've published citing Liquipedia data
  credits it by name with a link in its Sources section (e.g. "Liquipedia
  — an independent, community-maintained esports wiki, used here under its
  CC BY-SA license").
- We understand from [name]'s earlier note that citation via our reports
  is sufficient for that use case — noted and already in place.

**Two things we'd like to confirm directly, rather than assume:**

1. Does that same attribution standard (credit via our published
   reports/blog) also cover **committing Liquipedia-derived data to our
   public GitHub repo** in structured/machine-readable form
   (`data/reference/*.jsonl`), or would you want repo-level attribution
   handled differently — e.g. a more prominent notice, or a link back to
   the specific Liquipedia pages the data originated from?
2. Is there any **retention limit** we should be aware of for LPDB-sourced
   data specifically — i.e., is it fine for us to keep this data
   indefinitely once pulled, the way we already do for our own collected
   data, or does your license/terms expect periodic refresh or deletion?

**What's next on our end**: we're in the process of pulling tournament,
player, and broadcast data for the rest of our tracked titles (several are
already complete; the remainder are running on an automated schedule that
respects the rate limit above, not a manual burst). We'll follow up once
that's further along, and again before we publish anything derived from
player or broadcast data specifically, in case that raises different
considerations than tournament data has.

Happy to answer any questions about our usage pattern or share more detail
on any of the above.

Thanks again,
Jacob
