"""
Candidate Company Registry and Official Source Directory.
Contains verified exchange symbols, BSE scrip codes, official websites,
and document URLs for candidate companies from Top 500 MCA dataset.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

KNOWN_COMPANIES: List[Dict[str, Any]] = [
    {
        "company_name": "INDIAN OIL CORPORATION LIMITED",
        "aliases": ["IOCL", "INDIAN OIL", "INDIAN OIL CORP"],
        "symbol": "IOC",
        "bse_scrip": "530965",
        "cin": "L23201MH1959GOI011388",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://iocl.com",
        "csr_policy_url": "https://iocl.com/pages/csr-overview",
        "csr_policy_title": "Indian Oil Corporate Social Responsibility (CSR) Policy",
        "annual_reports": {
            "2023-24": {
                "title": "Indian Oil Annual Report 2023-24",
                "url": "https://iocl.com/download/Annual-Report-2023-24.pdf",
                "published_date": "2024-07-26",
                "nse_url": "https://archives.nseindia.com/corporate/annual/IOC_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/IOC_AR_2023-24.pdf",
            },
            "2022-23": {
                "title": "Indian Oil Annual Report 2022-23",
                "url": "https://iocl.com/download/Annual-Report-2022-23.pdf",
                "published_date": "2023-07-28",
                "nse_url": "https://archives.nseindia.com/corporate/annual/IOC_2022_2023.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/IOC_AR_2022-23.pdf",
            },
        },
        "brsr_reports": {
            "2023-24": {
                "title": "Indian Oil Business Responsibility & Sustainability Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/IOC_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/IOC_BRSR_2023-24.pdf",
                "published_date": "2024-07-26",
            }
        },
        "disclosures": [
            {
                "title": "Outcome of Board Meeting - Recommendation of Final Dividend and CSR Project Allocations",
                "financial_year": "2023-24",
                "category": "CSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/IOC_BM_Outcome_2024.pdf",
                "date": "2024-04-30",
            },
            {
                "title": "Business Responsibility and Sustainability Report (BRSR) for FY 2023-24",
                "financial_year": "2023-24",
                "category": "BRSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/IOC_BRSR_2023-24.pdf",
                "date": "2024-07-26",
            },
            {
                "title": "Annual Report for the Financial Year 2023-24 along with Notice of 65th AGM",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/IOC_AR_2023-24.pdf",
                "date": "2024-07-26",
            },
        ],
    },
    {
        "company_name": "CENTRAL COALFIELDS LIMITED",
        "aliases": ["CCL", "CENTRAL COALFIELDS"],
        "symbol": None,
        "bse_scrip": None,
        "cin": "U10200JH1956GOI000581",
        "is_listed": False,
        "exchanges": [],
        "website": "https://www.centralcoalfields.in",
        "csr_policy_url": "https://www.centralcoalfields.in/info/csr.php",
        "csr_policy_title": "Central Coalfields Limited CSR Policy (CIL Consolidated)",
        "notes": "Unlisted Miniratna PSU subsidiary of Coal India Limited. No direct exchange filings.",
        "annual_reports": {
            "2023-24": {
                "title": "CCL Annual Report & Accounts 2023-24",
                "url": "https://www.centralcoalfields.in/info/annual_report_2023_24.pdf",
                "published_date": "2024-08-10",
            }
        },
        "brsr_reports": {},
        "disclosures": [],
    },
    {
        "company_name": "GAIL (INDIA) LIMITED",
        "aliases": ["GAIL", "GAIL INDIA", "GAS AUTHORITY OF INDIA"],
        "symbol": "GAIL",
        "bse_scrip": "532155",
        "cin": "L40200DL1984GOI018783",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://gailonline.com",
        "csr_policy_url": "https://gailonline.com/pdf/CSR/GAIL_CSR_Policy.pdf",
        "csr_policy_title": "GAIL (India) Limited CSR Policy Guidelines",
        "annual_reports": {
            "2023-24": {
                "title": "GAIL Annual Report 2023-24",
                "url": "https://gailonline.com/pdf/Investors/GAIL_Annual_Report_2023_24.pdf",
                "published_date": "2024-07-31",
                "nse_url": "https://archives.nseindia.com/corporate/annual/GAIL_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/GAIL_AR_2023-24.pdf",
            },
            "2022-23": {
                "title": "GAIL Annual Report 2022-23",
                "url": "https://gailonline.com/pdf/Investors/GAIL_Annual_Report_2022_23.pdf",
                "published_date": "2023-08-01",
                "nse_url": "https://archives.nseindia.com/corporate/annual/GAIL_2022_2023.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/GAIL_AR_2022-23.pdf",
            },
        },
        "brsr_reports": {
            "2023-24": {
                "title": "GAIL Business Responsibility and Sustainability Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/GAIL_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/GAIL_BRSR_2023-24.pdf",
                "published_date": "2024-07-31",
            }
        },
        "disclosures": [
            {
                "title": "Disclosure under Regulation 34 - Annual Report for FY 2023-24 including BRSR",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/GAIL_AR_2023-24.pdf",
                "date": "2024-07-31",
            },
            {
                "title": "Intimation of Board Approval for CSR Annual Action Plan FY 2024-25",
                "financial_year": "2024-25",
                "category": "CSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/GAIL_CSR_AAP_2024.pdf",
                "date": "2024-05-16",
            },
        ],
    },
    {
        "company_name": "TATA STEEL LIMITED",
        "aliases": ["TATA STEEL", "TISCO"],
        "symbol": "TATASTEEL",
        "bse_scrip": "500470",
        "cin": "L27100MH1907PLC000260",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://www.tatasteel.com",
        "csr_policy_url": "https://www.tatasteel.com/media/13247/corporate-social-responsibility-policy.pdf",
        "csr_policy_title": "Tata Steel Corporate Social Responsibility Policy",
        "annual_reports": {
            "2023-24": {
                "title": "Tata Steel Integrated Report & Annual Accounts 2023-24",
                "url": "https://www.tatasteel.com/media/20701/integrated-report-2023-24.pdf",
                "published_date": "2024-06-05",
                "nse_url": "https://archives.nseindia.com/corporate/annual/TATASTEEL_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/TATASTEEL_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "Tata Steel Business Responsibility and Sustainability Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/TATASTEEL_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/TATASTEEL_BRSR_2023-24.pdf",
                "published_date": "2024-06-05",
            }
        },
        "disclosures": [
            {
                "title": "Integrated Report and Annual Accounts for FY 2023-24 along with BRSR",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/TATASTEEL_AR_2023-24.pdf",
                "date": "2024-06-05",
            },
            {
                "title": "Corporate Social Responsibility Committee - Update on Community Initiatives",
                "financial_year": "2023-24",
                "category": "CSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/TATASTEEL_CSR_2024.pdf",
                "date": "2024-05-29",
            },
        ],
    },
    {
        "company_name": "POWER GRID CORPORATION OF INDIA LIMITED",
        "aliases": ["POWERGRID", "POWER GRID", "PGCIL"],
        "symbol": "POWERGRID",
        "bse_scrip": "532898",
        "cin": "L40101DL1989GOI038121",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://www.powergrid.in",
        "csr_policy_url": "https://www.powergrid.in/sites/default/files/CSR_Policy_2021.pdf",
        "csr_policy_title": "Power Grid Corporation of India Limited CSR Policy",
        "annual_reports": {
            "2023-24": {
                "title": "POWERGRID 35th Annual Report 2023-24",
                "url": "https://www.powergrid.in/sites/default/files/Annual_Report_2023-24.pdf",
                "published_date": "2024-07-29",
                "nse_url": "https://archives.nseindia.com/corporate/annual/POWERGRID_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/POWERGRID_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "POWERGRID Business Responsibility and Sustainability Report (BRSR) 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/POWERGRID_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/POWERGRID_BRSR_2023-24.pdf",
                "published_date": "2024-07-29",
            }
        },
        "disclosures": [
            {
                "title": "Submission of Annual Report and BRSR for FY 2023-24",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/POWERGRID_AR_2023-24.pdf",
                "date": "2024-07-29",
            },
            {
                "title": "Disclosure of Corporate Social Responsibility Projects approved by Board",
                "financial_year": "2023-24",
                "category": "CSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/POWERGRID_CSR_2024.pdf",
                "date": "2024-05-22",
            },
        ],
    },
    {
        "company_name": "HINDUSTAN ZINC LIMITED",
        "aliases": ["HZL", "HINDUSTAN ZINC"],
        "symbol": "HINDZINC",
        "bse_scrip": "500188",
        "cin": "L27204RJ1966PLC001208",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://www.hzlindia.com",
        "csr_policy_url": "https://www.hzlindia.com/wp-content/uploads/CSR-Policy-HZL.pdf",
        "csr_policy_title": "Hindustan Zinc Limited CSR Policy",
        "annual_reports": {
            "2023-24": {
                "title": "Hindustan Zinc Integrated Annual Report 2023-24",
                "url": "https://www.hzlindia.com/wp-content/uploads/HZL-Integrated-Annual-Report-2023-24.pdf",
                "published_date": "2024-06-18",
                "nse_url": "https://archives.nseindia.com/corporate/annual/HINDZINC_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/HINDZINC_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "Hindustan Zinc BRSR 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/HINDZINC_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/HINDZINC_BRSR_2023-24.pdf",
                "published_date": "2024-06-18",
            }
        },
        "disclosures": [
            {
                "title": "Annual Report for FY 2023-24 and Notice of 58th AGM",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/HINDZINC_AR_2023-24.pdf",
                "date": "2024-06-18",
            }
        ],
    },
    {
        "company_name": "REC LIMITED",
        "aliases": ["REC", "RURAL ELECTRIFICATION CORPORATION"],
        "symbol": "RECLTD",
        "bse_scrip": "532955",
        "cin": "L40101DL1969GOI005095",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://recindia.nic.in",
        "csr_policy_url": "https://recindia.nic.in/uploads/files/CSR_Policy_REC.pdf",
        "csr_policy_title": "REC Limited Corporate Social Responsibility Policy",
        "annual_reports": {
            "2023-24": {
                "title": "REC Limited 55th Annual Report 2023-24",
                "url": "https://recindia.nic.in/uploads/files/REC_Annual_Report_2023-24.pdf",
                "published_date": "2024-08-08",
                "nse_url": "https://archives.nseindia.com/corporate/annual/RECLTD_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/RECLTD_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "REC Limited Business Responsibility & Sustainability Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/RECLTD_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/RECLTD_BRSR_2023-24.pdf",
                "published_date": "2024-08-08",
            }
        },
        "disclosures": [
            {
                "title": "Outcome of Board Meeting - CSR Project Sanctions and Annual Report Submission",
                "financial_year": "2023-24",
                "category": "CSR",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/RECLTD_CSR_2024.pdf",
                "date": "2024-04-30",
            }
        ],
    },
    {
        "company_name": "NESTLE INDIA LIMITED",
        "aliases": ["NESTLE", "NESTLE INDIA"],
        "symbol": "NESTLEIND",
        "bse_scrip": "500790",
        "cin": "L15202DL1959PLC003250",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://www.nestle.in",
        "csr_policy_url": "https://www.nestle.in/sites/g/files/pydfqk451/files/2021-08/CSR-Policy-Nestle-India.pdf",
        "csr_policy_title": "Nestlé India Policy on Corporate Social Responsibility",
        "annual_reports": {
            "2023-24": {
                "title": "Nestlé India Annual Report 2023-24",
                "url": "https://www.nestle.in/sites/g/files/pydfqk451/files/2024-06/Annual-Report-2023-24.pdf",
                "published_date": "2024-06-12",
                "nse_url": "https://archives.nseindia.com/corporate/annual/NESTLEIND_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/NESTLEIND_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "Nestlé India Business Responsibility & Sustainability Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/NESTLEIND_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/NESTLEIND_BRSR_2023-24.pdf",
                "published_date": "2024-06-12",
            }
        },
        "disclosures": [
            {
                "title": "Submission of Annual Report and BRSR for Financial Year ended 31st March 2024",
                "financial_year": "2023-24",
                "category": "Annual Report",
                "url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/NESTLEIND_AR_2023-24.pdf",
                "date": "2024-06-12",
            }
        ],
    },
    {
        "company_name": "NATIONAL ALUMINIUM CO LTD",
        "aliases": ["NALCO", "NATIONAL ALUMINIUM"],
        "symbol": "NATIONALUM",
        "bse_scrip": "532234",
        "cin": "L27203OR1981GOI000920",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://nalcoindia.com",
        "csr_policy_url": "https://nalcoindia.com/wp-content/uploads/2021/07/NALCO-CSR-Policy.pdf",
        "csr_policy_title": "NALCO Corporate Social Responsibility Policy",
        "annual_reports": {
            "2023-24": {
                "title": "NALCO 43rd Annual Report 2023-24",
                "url": "https://nalcoindia.com/wp-content/uploads/2024/08/Annual-Report-2023-24.pdf",
                "published_date": "2024-08-20",
                "nse_url": "https://archives.nseindia.com/corporate/annual/NATIONALUM_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/NATIONALUM_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "NALCO BRSR Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/NATIONALUM_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/NATIONALUM_BRSR_2023-24.pdf",
                "published_date": "2024-08-20",
            }
        },
        "disclosures": [],
    },
    {
        "company_name": "NORTHERN COALFIELDS LIMITED",
        "aliases": ["NCL", "NORTHERN COALFIELDS"],
        "symbol": None,
        "bse_scrip": None,
        "cin": "U10102MP1985GOI003160",
        "is_listed": False,
        "exchanges": [],
        "website": "https://www.nclcil.in",
        "csr_policy_url": "https://www.nclcil.in/page/csr-policy",
        "csr_policy_title": "Northern Coalfields Limited CSR Policy",
        "notes": "Unlisted subsidiary of Coal India Limited.",
        "annual_reports": {},
        "brsr_reports": {},
        "disclosures": [],
    },
    {
        "company_name": "DIVI'S LABORATORIES LIMITED",
        "aliases": ["DIVIS LABS", "DIVIS", "DIVIS LABORATORIES"],
        "symbol": "DIVISLAB",
        "bse_scrip": "532488",
        "cin": "L24110TG1990PLC011854",
        "is_listed": True,
        "exchanges": ["NSE", "BSE"],
        "website": "https://www.divislabs.com",
        "csr_policy_url": "https://www.divislabs.com/wp-content/uploads/2021/06/CSR-Policy-Divis.pdf",
        "csr_policy_title": "Divi's Laboratories Corporate Social Responsibility Policy",
        "annual_reports": {
            "2023-24": {
                "title": "Divi's Laboratories 34th Annual Report 2023-24",
                "url": "https://www.divislabs.com/wp-content/uploads/2024/07/Annual-Report-2023-24.pdf",
                "published_date": "2024-07-15",
                "nse_url": "https://archives.nseindia.com/corporate/annual/DIVISLAB_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/DIVISLAB_AR_2023-24.pdf",
            }
        },
        "brsr_reports": {
            "2023-24": {
                "title": "Divi's Laboratories BRSR Report 2023-24",
                "url": "https://archives.nseindia.com/corporate/brsr/DIVISLAB_BRSR_2023_2024.pdf",
                "bse_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/DIVISLAB_BRSR_2023-24.pdf",
                "published_date": "2024-07-15",
            }
        },
        "disclosures": [],
    },
]


def normalize_query(query: Optional[str]) -> str:
    """Normalizes query string by stripping punctuation, extra whitespace and uppercasing."""
    if not query:
        return ""
    cleaned = re.sub(r"[.,/#!$%^&*;:{}=\-_`~()]", " ", query.upper())
    return re.sub(r"\s+", " ", cleaned).strip()


def find_in_registry(
    company_name: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Optional[Tuple[Dict[str, Any], float, str]]:
    """
    Finds a company in the registry by name, alias, or symbol.
    Returns (company_dict, match_confidence, match_type) or None.
    """
    if symbol:
        sym_clean = symbol.strip().upper()
        for c in KNOWN_COMPANIES:
            if c.get("symbol") and c["symbol"].upper() == sym_clean:
                return c, 1.0, "symbol"

    if not company_name:
        return None

    target = normalize_query(company_name)

    # 1. Exact name match
    for c in KNOWN_COMPANIES:
        if normalize_query(c["company_name"]) == target:
            return c, 1.0, "exact_name"

    # 2. Exact alias match
    for c in KNOWN_COMPANIES:
        for alias in c.get("aliases", []):
            if normalize_query(alias) == target:
                return c, 0.95, "alias"

    # 3. Substring match
    for c in KNOWN_COMPANIES:
        c_norm = normalize_query(c["company_name"])
        if target in c_norm or c_norm in target:
            return c, 0.85, "fuzzy_substring"
        for alias in c.get("aliases", []):
            a_norm = normalize_query(alias)
            if target in a_norm or a_norm in target:
                return c, 0.80, "fuzzy_alias"

    return None
