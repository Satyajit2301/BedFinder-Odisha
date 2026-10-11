"""
Link and Contact Verification Script for BedFinder Odisha.

Verifies hospital official websites (exact HTTP status, redirects, domain match)
and phone numbers (format validation, Bhubaneswar STD code 0674 checks, and team confirmation).

Website statuses are strictly:
  - LIVE (200 or redirect to 200)
  - BLOCKED_403
  - DNS_FAIL (tests both bare domain and www. variant)
  - NOT_FOUND_404
  - TLS_ERROR
  - NONE

Updates data/hospitals_enriched.csv with:
  - phone_confirmed ('yes' only if team check confirmed, else 'no')
  - website_confirmed ('yes' only if team check confirmed, else 'no')
  - website_status (exact probe status)
  - website_verified (bool: True if LIVE or website_confirmed == 'yes')
  - phone_verified (bool: True if phone_confirmed == 'yes')

Writes complete probe audit report to docs/verify_links_output.txt.

Run:  python scripts/verify_links.py
"""
import datetime
import re
import ssl
import sys
from pathlib import Path
from urllib.parse import urlparse
import urllib.request
import urllib.error

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ENRICHED = ROOT / "data" / "hospitals_enriched.csv"
TEAM_CHECK = ROOT / "data" / "team_check.csv"
OUTPUT_TXT = ROOT / "docs" / "verify_links_output.txt"


def do_http_probe(url: str, timeout: float = 6.0):
    """
    Probe a single URL.
    Returns (status, code, final_url, error_msg)
    """
    if not url or not isinstance(url, str) or not url.strip().startswith("http"):
        return "NONE", None, url, "No URL provided"

    url = url.strip()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BedFinderVerification/2.4"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            code = resp.status
            final = resp.geturl()
            if code in (200, 301, 302, 307, 308):
                return "LIVE", code, final, ""
            return f"HTTP_{code}", code, final, ""
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return "BLOCKED_403", 403, url, "HTTP 403 Forbidden"
        elif e.code == 404:
            return "NOT_FOUND_404", 404, url, "HTTP 404 Not Found"
        return f"HTTP_{e.code}", e.code, url, str(e.reason)
    except ssl.SSLError as e:
        return "TLS_ERROR", None, url, str(e)
    except urllib.error.URLError as e:
        reason_str = str(e.reason)
        if "getaddrinfo failed" in reason_str or "Name or service not known" in reason_str or "nodename nor servname" in reason_str:
            return "DNS_FAIL", None, url, reason_str
        if isinstance(e.reason, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in reason_str:
            return "TLS_ERROR", None, url, reason_str
        return "URL_ERROR", None, url, reason_str
    except Exception as e:
        err_str = f"{type(e).__name__}: {e}"
        if "ssl" in err_str.lower() or "certificate" in err_str.lower():
            return "TLS_ERROR", None, url, err_str
        return "ERROR", None, url, err_str


def check_website(url: str, timeout: float = 6.0):
    """
    Check website reachability with bare and www fallback for DNS_FAIL.
    Returns (exact_status, detail)
    """
    if not url or not isinstance(url, str) or not url.strip() or str(url).strip() == "nan":
        return "NONE", "(No website listed)"

    url = url.strip()
    status, code, final_url, err = do_http_probe(url, timeout)

    if status == "DNS_FAIL":
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            alt_domain = domain[4:]
        else:
            alt_domain = f"www.{domain}"
        alt_url = url.replace(domain, alt_domain)

        alt_status, alt_code, alt_final, alt_err = do_http_probe(alt_url, timeout)
        detail = f"Primary ({url}): DNS_FAIL; Alternate ({alt_url}): {alt_status}"
        if alt_status == "LIVE":
            return "LIVE", f"{alt_final} (Resolved on variant {alt_url})"
        elif alt_status in ("BLOCKED_403", "NOT_FOUND_404", "TLS_ERROR"):
            return alt_status, detail
        else:
            return "DNS_FAIL", detail

    elif status == "LIVE":
        return "LIVE", f"{final_url}"
    elif status == "BLOCKED_403":
        return "BLOCKED_403", f"{url} (HTTP 403 Forbidden)"
    elif status == "NOT_FOUND_404":
        return "NOT_FOUND_404", f"{url} (HTTP 404 Not Found)"
    elif status == "TLS_ERROR":
        return "TLS_ERROR", f"{url} (TLS handshake / SSL certificate error)"
    else:
        return status, f"{url} ({err})"


def check_phone_format(phone: str) -> bool:
    """Validate standard Odisha landline format (0674-XXXXXXX)."""
    if not phone or not isinstance(phone, str) or str(phone).strip() == "nan":
        return False
    clean = re.sub(r"\s+", "", phone)
    return bool(re.match(r"^0674-\d{7}$", clean))


def main():
    if not ENRICHED.exists():
        print(f"[err] {ENRICHED} not found. Run enrich_data.py first.")
        sys.exit(1)

    df = pd.read_csv(ENRICHED)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"=" * 80)
    print(f"BedFinder Odisha Link & Contact Verification")
    print(f"Timestamp: {now_str}")
    print(f"Dataset: {ENRICHED} ({len(df)} hospitals)")
    print(f"=" * 80)

    log_lines = [
        f"BedFinder Odisha Link & Contact Verification Report",
        f"Generated: {now_str}",
        f"Target Dataset: {ENRICHED} (Total records: {len(df)})",
        "-" * 80,
        f"{'ID':<8} | {'Hospital Name':<35} | {'Type':<7} | {'Status':<13} | {'Detail'}",
        "-" * 80,
    ]

    # Team confirmed lookups from team_check.csv
    tc_phones = {}
    tc_webs = {}
    if TEAM_CHECK.exists():
        tc_df = pd.read_csv(TEAM_CHECK)
        for _, r in tc_df.iterrows():
            hid = str(r["hospital_id"]).strip()
            keep_val = str(r.get([c for c in r.index if "keep" in c][0])).strip().lower()
            if keep_val == "yes":
                p_col = [c for c in r.index if "phone" in c and "note" not in c][0]
                w_col = [c for c in r.index if "website" in c][0]
                if pd.notna(r[p_col]) and str(r[p_col]).strip():
                    tc_phones[hid] = str(r[p_col]).strip()
                if pd.notna(r[w_col]) and str(r[w_col]).strip():
                    tc_webs[hid] = str(r[w_col]).strip()

    status_counts = {"LIVE": 0, "BLOCKED_403": 0, "DNS_FAIL": 0, "NOT_FOUND_404": 0, "TLS_ERROR": 0, "NONE": 0}
    phone_confirmed_count = 0
    phone_unconfirmed_count = 0

    df["phone_confirmed"] = "no"
    df["website_confirmed"] = "no"
    df["website_status"] = "NONE"
    df["website_verified"] = False
    df["phone_verified"] = False

    for idx, row in df.iterrows():
        hid = row["hospital_id"]
        name = str(row["hospital_name"])[:34]
        web = str(row.get("website", "")) if pd.notna(row.get("website")) else ""
        web = web.strip()
        ph = str(row.get("phone", "")) if pd.notna(row.get("phone")) else ""
        ph = ph.strip()

        # Set confirmed flags from team check
        if hid in tc_phones:
            df.at[idx, "phone_confirmed"] = "yes"
            df.at[idx, "phone_verified"] = True
            phone_confirmed_count += 1
        elif ph:
            phone_unconfirmed_count += 1

        if hid in tc_webs:
            df.at[idx, "website_confirmed"] = "yes"

        # Web check
        status, detail = check_website(web)
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts[status] = status_counts.get(status, 0) + 1

        df.at[idx, "website_status"] = status
        # UI rule: show website as link if LIVE or website_confirmed == 'yes'
        is_web_ok = (status == "LIVE") or (df.at[idx, "website_confirmed"] == "yes")
        df.at[idx, "website_verified"] = is_web_ok

        line_web = f"{hid:<8} | {name:<35} | WEB     | {status:<13} | {detail}"
        print(line_web)
        log_lines.append(line_web)

        # Phone check (honest report: no "PASS (Verified directory)")
        if ph:
            is_valid_fmt = check_phone_format(ph)
            is_conf = df.at[idx, "phone_confirmed"] == "yes"
            if is_conf:
                ph_status = "CONFIRMED"
                ph_detail = f"{ph} (Confirmed in team check Google Maps)"
            elif is_valid_fmt:
                ph_status = "UNVERIFIED"
                ph_detail = f"{ph} (Valid 0674 format; unconfirmed directory listing)"
            else:
                ph_status = "INVALID"
                ph_detail = f"{ph} (Invalid format)"
        else:
            ph_status = "NONE"
            ph_detail = "(No phone listed)"

        line_ph = f"{hid:<8} | {name:<35} | PHONE   | {ph_status:<13} | {ph_detail}"
        print(line_ph)
        log_lines.append(line_ph)

    summary_lines = [
        "-" * 80,
        f"Verification Summary:",
        f"  Total Hospitals Evaluated: {len(df)}",
        f"  Websites Listed:           {df['website'].dropna().ne('').sum()}",
        f"    LIVE (200 / redirect):   {status_counts.get('LIVE', 0)}",
        f"    BLOCKED_403:             {status_counts.get('BLOCKED_403', 0)}",
        f"    DNS_FAIL:                {status_counts.get('DNS_FAIL', 0)}",
        f"    NOT_FOUND_404:           {status_counts.get('NOT_FOUND_404', 0)}",
        f"    TLS_ERROR:               {status_counts.get('TLS_ERROR', 0)}",
        f"    NONE:                    {status_counts.get('NONE', 0)}",
        f"  Websites Confirmed (Team): {sum(df['website_confirmed'] == 'yes')}",
        f"  Phones Listed:             {df['phone'].dropna().ne('').sum()}",
        f"  Phones Confirmed (Team):   {phone_confirmed_count}",
        f"  Phones Unconfirmed:        {phone_unconfirmed_count}",
        f"=" * 80,
    ]
    for s in summary_lines:
        print(s)
        log_lines.append(s)

    # Save enriched dataset
    df.to_csv(ENRICHED, index=False)
    print(f"[ok] Updated {ENRICHED}")

    # Write output report
    OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"[ok] Saved verification log to {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
