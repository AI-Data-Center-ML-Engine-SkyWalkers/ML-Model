"""Share of real-time hours with LMP <= $0/MWh at the pricing node nearest each county (last two full years).

BLOCKED: no keyless route gives node-level prices WITH node locations for all seven ISOs.
- gridstatus needs credentials for PJM (PJM_API_KEY), ERCOT (ERCOT API username/password + subscription key) and
  ISO-NE (ISONE_API_USERNAME / ISONE_API_PASSWORD). All are free registrations.
- ISOs do not publish pricing-node coordinates, so "nearest node" needs a node-location table anyway; the
  hub/zone fallback needs zone boundaries, which are not published for most ISOs either.
- Berkeley Lab's Wholesale Electricity Prices (WEP) tool (v2026.1) has node-level aggregated data (including
  negative-price frequency) with a "download selected data" button, but emp.lbl.gov serves a browser challenge
  (HTTP 403) to scripted requests, so the file has to be downloaded by hand into data/raw/lbnl_wep/.
Features stay NaN (never 0) until one of these is provided.
"""
from src.common.io import RAW, set_status

FEATURES = ["pwr_neg_price_pct_hours", "pwr_neg_price_available"]
WEP_DIR = RAW / "lbnl_wep"


def main():
    files = sorted(WEP_DIR.glob("*")) if WEP_DIR.exists() else []
    msg = ("Needs either PJM/ERCOT/ISO-NE API credentials for gridstatus (free registrations) plus a node-location "
           "table, or a manual download of Berkeley Lab WEP tool data (https://emp.lbl.gov/wholesale-electricity-"
           "prices-wep-tool, 'download selected data'; site blocks scripted requests) into data/raw/lbnl_wep/.")
    if files:
        msg = f"Found {[f.name for f in files]} in data/raw/lbnl_wep/ but no parser yet. " + msg
    set_status("lmp_negative_prices", "BLOCKED", msg, FEATURES)


if __name__ == "__main__":
    main()
