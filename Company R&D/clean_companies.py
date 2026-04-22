"""
Clean and deduplicate the patent company CSV.
Priority: (1) company_name column, (2) CANONICAL dict, (3) first_applicant as-is.
"""
import csv
from collections import defaultdict

INPUT  = "/Users/humza/Downloads/Copy of companies_manually_cleaned - companies_manually_cleaned.csv"
OUTPUT = "/Users/humza/Downloads/companies_cleaned.csv"

# ── Extra mappings not covered by the company_name column ────────────────────
# key: normalize(first_applicant) → (official_name, entity_type, timeline_note)
EXTRA = {
    # TSMC sub-entities (company_name blank in source)
    "tsmc china company limited":          ("Taiwan Semiconductor Manufacturing Company Limited", "Subsidiary", "TSMC China fab"),
    "tsmc nanjing company limited":        ("Taiwan Semiconductor Manufacturing Company Limited", "Subsidiary", "TSMC Nanjing fab"),

    # GlobalFoundries
    "globalfoundries singapore pte ltd":   ("GlobalFoundries Inc.",        "Subsidiary", "Singapore entity"),

    # Infineon
    "infineon technologies austria ag":    ("Infineon Technologies AG",    "Subsidiary", "Austria entity"),
    "infineon technologies dresden gmbh co kg": ("Infineon Technologies AG","Subsidiary","Dresden fab"),

    # STMicro (company_name only covers stmicroelectronics international nv)
    "stmicroelectronics srl":              ("STMicroelectronics N.V.",     "Subsidiary", "Italy entity"),
    "stmicroelectronics inc":              ("STMicroelectronics N.V.",     "Subsidiary", "US entity"),
    "stmicroelectronics rousset sas":      ("STMicroelectronics N.V.",     "Subsidiary", "France – Rousset"),
    "stmicroelectronics crolles 2 sas":    ("STMicroelectronics N.V.",     "Subsidiary", "France – Crolles"),
    "stmicroelectronics grenoble 2 sas":   ("STMicroelectronics N.V.",     "Subsidiary", "France – Grenoble"),
    "stmicroelectronics pte ltd":          ("STMicroelectronics N.V.",     "Subsidiary", "Singapore entity"),
    "stmicroelectronics tours sas":        ("STMicroelectronics N.V.",     "Subsidiary", "France – Tours"),
    "stmicroelectronics international nv": ("STMicroelectronics N.V.",     "Parent",     ""),

    # NXP
    "nxp bv":                              ("NXP Semiconductors N.V.",     "Subsidiary", "Netherlands holding entity"),
    "nxp usa inc":                         ("NXP Semiconductors N.V.",     "Subsidiary", "US entity"),

    # Baidu
    "beijing baidu netcom science technology co ltd":    ("Baidu, Inc.", "Subsidiary", "Name variant – core entity"),
    "beijing baidu netcom science and technology co ltd":("Baidu, Inc.", "Subsidiary", "Core operating entity"),
    "baidu usa llc":                                     ("Baidu, Inc.", "Subsidiary", "US entity"),
    "baidu online network technology beijing co ltd":    ("Baidu, Inc.", "Subsidiary", "Online services entity"),
    "baiducom times technology beijing co ltd":          ("Baidu, Inc.", "Subsidiary", "Technology entity"),

    # Huawei
    "huawei technologies coltd":               ("Huawei Technologies Co., Ltd.", "Duplicate",  "Name variant"),
    "huawei digital power technologies co ltd":("Huawei Technologies Co., Ltd.", "Subsidiary", "Digital Power division"),
    "huawei cloud computing technologies co ltd":("Huawei Technologies Co., Ltd.","Subsidiary","Cloud division"),

    # Tencent
    "tencent america llc":                     ("Tencent Holdings Limited",       "Subsidiary", "US entity"),

    # Meta / Facebook
    "meta platforms technologies llc":         ("Meta Platforms, Inc.",           "Subsidiary", "Reality Labs / hardware"),
    "facebook inc":                            ("Meta Platforms, Inc.",           "Predecessor","Renamed Meta Oct 2021"),
    "facebook technologies llc":               ("Meta Platforms, Inc.",           "Subsidiary", "Now Meta Platforms Technologies LLC"),

    # Samsung sub-entities (separate listed companies within Samsung group)
    "samsung electronics coltd":               ("Samsung Electronics Co., Ltd.",  "Duplicate",  "Name variant"),
    "samsung electromechanics co ltd":          ("Samsung Electro-Mechanics Co., Ltd.", "Samsung subsidiary", "~38% owned by Samsung Electronics"),
    "samsung display co ltd":                   ("Samsung Display Co., Ltd.",      "Samsung subsidiary", "100% Samsung Electronics; display panels"),
    "samsung sds co ltd":                       ("Samsung SDS Co., Ltd.",          "Samsung subsidiary", "IT/cloud services arm"),

    # Sony group
    "sony corporation":                        ("Sony Group Corporation",          "Predecessor","Renamed Sony Group Corp Apr 2021"),
    "sony semiconductor solutions corporation":("Sony Group Corporation",          "Subsidiary", "Image sensor division"),
    "sony interactive entertainment inc":      ("Sony Group Corporation",          "Subsidiary", "PlayStation division"),

    # Toshiba group
    "toshiba memory corporation":              ("Kioxia Corporation",              "Predecessor","Spun off; renamed Kioxia Oct 2019"),
    "toshiba materials co ltd":                ("Toshiba Corporation",             "Subsidiary", "Materials division"),
    "toshiba digital solutions corporation":   ("Toshiba Corporation",             "Subsidiary", "IT services division"),
    "kabushiki kaisha toshiba":                ("Toshiba Corporation",             "Parent",     ""),

    # Hitachi group (distinct subsidiaries)
    "hitachi astemo ltd":                      ("Hitachi, Ltd.",                   "Subsidiary", "Auto JV w/ Honda; est. Jan 2021"),
    "hitachi energy ltd":                      ("Hitachi, Ltd.",                   "Subsidiary", "~80% owned; power grids"),
    "hitachi hightech corporation":            ("Hitachi, Ltd.",                   "Subsidiary", "Semiconductor equipment"),
    "hitachi automotive systems ltd":          ("Hitachi, Ltd.",                   "Subsidiary", "Merged into Hitachi Astemo Jan 2021"),
    "hitachi chemical company ltd":            ("Resonac Corporation",             "Former subsidiary","Sold 2020; merged into Showa Denko → Resonac 2023"),
    "hitachi kokusai electric inc":            ("Kokusai Electric Corporation",    "Former subsidiary","Sold to KKR 2018; re-IPO Oct 2023"),
    "hitachi power semiconductor device ltd":  ("Hitachi, Ltd.",                   "Subsidiary", "Power semiconductors"),

    # Mitsubishi group (separate companies)
    "mitsubishi electric research laboratories inc": ("Mitsubishi Electric Corporation","Subsidiary","US R&D lab"),
    # mitsubishi materials, heavy industries, chemical → kept separate (independent companies)

    # Adeia / Xperi / Tessera / Invensas
    "adeia semiconductor technologies llc":    ("Adeia Inc.",                      "Subsidiary", "IP licensing entity"),
    "adeia semiconductor solutions llc":       ("Adeia Inc.",                      "Subsidiary", "IP licensing entity"),
    "adeia semiconductor inc":                 ("Adeia Inc.",                      "Subsidiary", "IP licensing entity"),
    "invensas corporation":                    ("Adeia Inc.",                      "Predecessor","Acquired by Xperi; part of Adeia since 2022"),
    "invensas bonding technologies inc":       ("Adeia Inc.",                      "Subsidiary", "Bonding tech licensing"),
    "tessera inc":                             ("Adeia Inc.",                      "Predecessor","Legacy entity; now Adeia"),
    "tessera llc":                             ("Adeia Inc.",                      "Subsidiary", "Legacy entity"),
    "xcelsis corporation":                     ("Adeia Inc.",                      "Subsidiary", "3D IC bonding IP"),
    "adeia semiconductor bonding technologies inc": ("Adeia Inc.",                 "Parent",     ""),

    # Alpha and Omega Semiconductor
    "alpha and omega semiconductor cayman ltd":    ("Alpha and Omega Semiconductor Limited","Subsidiary","Cayman holding entity"),
    "alpha and omega semiconductor incorporated":  ("Alpha and Omega Semiconductor Limited","Subsidiary","US entity"),

    # Delta Electronics
    "delta electronics shanghai co ltd":       ("Delta Electronics, Inc.",         "Subsidiary", "Shanghai manufacturing"),
    "delta electronics shanghai coltd":        ("Delta Electronics, Inc.",         "Duplicate",  "Name variant"),

    # Lenovo
    "lenovo enterprise solutions singapore pte ltd":("Lenovo Group Limited",       "Subsidiary", "Enterprise Solutions – Singapore"),
    "lenovo singapore pte ltd":                ("Lenovo Group Limited",            "Subsidiary", "Singapore hub"),
    "lenovo beijing limited":                  ("Lenovo Group Limited",            "Subsidiary", "Beijing entity"),

    # Qualcomm
    "qualcomm technologies inc":               ("Qualcomm Incorporated",           "Subsidiary", "Wholly-owned R&D subsidiary"),

    # NEC
    "nec laboratories america inc":            ("NEC Corporation",                 "Subsidiary", "US research lab"),
    "nec laboratories europe gmbh":            ("NEC Corporation",                 "Subsidiary", "Europe research lab"),
    "nec platforms ltd":                       ("NEC Corporation",                 "Subsidiary", "IT platforms"),

    # SMIC
    "semiconductor manufacturing international beijing corporation": ("Semiconductor Manufacturing International Corporation","Subsidiary","Beijing fab"),
    "semiconductor manufacturing international shanghai corporation":("Semiconductor Manufacturing International Corporation","Subsidiary","Shanghai fab"),
    "smic new technology research and development shanghai corporation":("Semiconductor Manufacturing International Corporation","Subsidiary","Shanghai R&D"),

    # Innoscience
    "innoscience suzhou technology co ltd":    ("Innoscience Technology Co., Ltd.","Subsidiary","Suzhou fab"),
    "innoscience zhuhai technology co ltd":    ("Innoscience Technology Co., Ltd.","Subsidiary","Zhuhai fab"),
    "innoscience suzhou semiconductor co ltd": ("Innoscience Technology Co., Ltd.","Subsidiary","Suzhou semiconductor entity"),

    # CEA (encoding variants)
    "commissariat a lenergie atomique et aux energies alternatives":    ("CEA (Commissariat à l'énergie atomique et aux énergies alternatives)","Parent",""),
    "commissariat à lénergie atomique et aux énergies alternatives":   ("CEA (Commissariat à l'énergie atomique et aux énergies alternatives)","Duplicate","Encoding variant"),
    "commissariat à lenergie atomique et aux energies alternatives":   ("CEA (Commissariat à l'énergie atomique et aux énergies alternatives)","Duplicate","Encoding variant"),

    # Fraunhofer (encoding variants)
    "fraunhofergesellschaft zur foerderung der angewandten forschung ev":("Fraunhofer-Gesellschaft","Parent",""),
    "fraunhofergesellschaft zur förderung der angewandten forschung ev": ("Fraunhofer-Gesellschaft","Duplicate","Encoding variant"),

    # Cree → Wolfspeed
    "cree inc":                                ("Wolfspeed, Inc.",                 "Predecessor","Rebranded to Wolfspeed Oct 2021"),

    # Salesforce
    "salesforcecom inc":                       ("Salesforce, Inc.",                "Duplicate",  "Renamed from salesforce.com to Salesforce Aug 2022"),

    # VMware (acquired Broadcom Nov 2023)
    "vmware inc":                              ("VMware LLC",                      "Predecessor","Acquired by Broadcom Nov 2023; converted to LLC"),

    # Realtek
    "realtek semiconductor corp":              ("Realtek Semiconductor Corp.",     "Duplicate",  "Name variant"),

    # Wistron
    "wistron corp":                            ("Wistron Corporation",             "Duplicate",  "Name variant"),

    # Kia
    "kia motors corporation":                  ("Kia Corporation",                 "Duplicate",  "Renamed to Kia Corporation Jan 2021"),

    # MediaTek
    "mediatek singapore pte ltd":              ("MediaTek Inc.",                   "Subsidiary", "Singapore entity"),

    # SJ Semiconductor
    "sj semiconductorjiangyin corporation":    ("SJ Semiconductor (Jiangyin) Corporation","Duplicate","Name variant"),

    # Microchip Technology
    "microchip technology inc":                ("Microchip Technology Incorporated","Duplicate", "Name variant"),

    # Aptiv
    "aptiv technologies ag":                   ("Aptiv PLC",                       "Subsidiary", "Swiss entity"),
    "aptiv technologies limited":              ("Aptiv PLC",                       "Subsidiary", "Ireland entity"),

    # Asia Vital Components
    "asia vital components china co ltd":      ("Asia Vital Components Co., Ltd.", "Subsidiary", "China entity"),

    # Invention and Collaboration Lab
    "invention and collaboration laboratory pte ltd": ("Invention and Collaboration Laboratory","Subsidiary","Singapore entity"),

    # Showa Denko / Resonac
    "showa denko kk":                          ("Resonac Corporation",             "Predecessor","Merged w/ Hitachi Chemical; rebranded Resonac Jan 2023"),
    "showa denko materials co ltd":            ("Resonac Corporation",             "Predecessor","Former Hitachi Chemical → merged into Resonac"),

    # Alibaba
    "alibaba china co ltd":                    ("Alibaba Group Holding Limited",   "Subsidiary", "China entity"),
    "advanced new technologies co ltd":        ("Ant Group Co., Ltd.",             "Subsidiary", "Ant Group / fintech affiliate"),

    # Alipay
    "alipay hangzhou information technology co ltd": ("Ant Group Co., Ltd.",       "Subsidiary", "Alipay operating entity"),

    # ByteDance entities
    "suzhou metabrain intelligent technology co ltd":("ByteDance Ltd.",            "Subsidiary", "AI chip division"),
    "beijing bytedance network technology co ltd":   ("ByteDance Ltd.",            "Subsidiary", "Core ByteDance entity"),
    "beijing volcano engine technology co ltd":      ("ByteDance Ltd.",            "Subsidiary", "Volcano Engine cloud platform"),
    "beijing zitiao network technology co ltd":      ("ByteDance Ltd.",            "Subsidiary", "Content/Toutiao entity"),

    # ── Top companies missing from company_name column ────────────────────────
    "samsung electronics co ltd":              ("Samsung Electronics Co., Ltd.",   "Parent",     ""),
    "texas instruments incorporated":          ("Texas Instruments Incorporated",  "Parent",     ""),
    "sk hynix inc":                            ("SK Hynix Inc.",                   "Parent",     ""),
    "qualcomm incorporated":                   ("Qualcomm Incorporated",           "Parent",     ""),
    "mitsubishi electric corporation":         ("Mitsubishi Electric Corporation", "Independent","Separate from other Mitsubishi group cos"),
    "dell products lp":                        ("Dell Technologies Inc.",          "Subsidiary", "Primary product entity"),
    "nanya technology corporation":            ("Nanya Technology Corporation",    "Parent",     ""),
    "united microelectronics corp":            ("United Microelectronics Corporation","Parent",  ""),
    "huawei technologies co ltd":              ("Huawei Technologies Co., Ltd.",   "Parent",     ""),
    "fuji electric co ltd":                    ("Fuji Electric Co., Ltd.",         "Parent",     ""),
    "kioxia corporation":                      ("Kioxia Corporation",              "Parent",     "Spun off from Toshiba; formerly Toshiba Memory"),
    "rohm co ltd":                             ("ROHM Co., Ltd.",                  "Parent",     ""),
    "fujitsu limited":                         ("Fujitsu Limited",                 "Parent",     ""),
    "tokyo electron limited":                  ("Tokyo Electron Limited",          "Parent",     ""),
    "semiconductor energy laboratory co ltd":  ("Semiconductor Energy Laboratory Co., Ltd.","Parent","Private; Japan"),
    "asm ip holding bv":                       ("ASM International N.V.",          "Subsidiary", "US IP holding entity"),
    "changxin memory technologies inc":        ("Changxin Memory Technologies, Inc.","Parent",  "Chinese DRAM maker (CXMT)"),
    "renesas electronics corporation":         ("Renesas Electronics Corporation", "Parent",     ""),
    "sandisk technologies llc":                ("SanDisk Corporation",             "Subsidiary", "WD subsidiary; spun off as SanDisk Corp Feb 2024"),
    "oracle international corporation":        ("Oracle Corporation",              "Subsidiary", "Primary operating entity"),
    "robert bosch gmbh":                       ("Robert Bosch GmbH",               "Parent",     "Private"),
    "denso corporation":                       ("DENSO Corporation",               "Parent",     "Toyota group affiliate"),
    "rambus inc":                              ("Rambus Inc.",                     "Parent",     ""),
    "nec corporation":                         ("NEC Corporation",                 "Parent",     ""),
    "kokusai electric corporation":            ("Kokusai Electric Corporation",    "Parent",     "Sold by Hitachi to KKR 2018; re-IPO Oct 2023"),
    "western digital technologies inc":        ("Western Digital Corporation",     "Subsidiary", "Primary operating entity"),
    "lam research corporation":                ("Lam Research Corporation",        "Parent",     ""),
    "mediatek inc":                            ("MediaTek Inc.",                   "Parent",     ""),
    "cisco technology inc":                    ("Cisco Systems, Inc.",             "Subsidiary", "Patent/technology entity"),
    "carrier corporation":                     ("Carrier Global Corporation",      "Subsidiary", "Spun off from UTC Apr 2020"),
    "daikin industries ltd":                   ("Daikin Industries, Ltd.",         "Parent",     ""),
    "canon kabushiki kaisha":                  ("Canon Inc.",                      "Parent",     ""),
    "winbond electronics corp":                ("Winbond Electronics Corporation", "Parent",     ""),
    "sony semiconductor solutions corporation":("Sony Group Corporation",          "Subsidiary", "Image sensor division"),
    "sony corporation":                        ("Sony Group Corporation",          "Predecessor","Renamed Sony Group Corp Apr 2021"),
    "sony group corporation":                  ("Sony Group Corporation",          "Parent",     ""),
    "sap se":                                  ("SAP SE",                          "Parent",     ""),
    "hitachi ltd":                             ("Hitachi, Ltd.",                   "Parent",     ""),
    "nippon telegraph and telephone corporation":("NTT Corporation",               "Parent",     ""),
    "shinko electric industries co ltd":       ("Shinko Electric Industries Co., Ltd.","Parent",""),
    "quanta computer inc":                     ("Quanta Computer Inc.",            "Parent",     ""),
    "wolfspeed inc":                           ("Wolfspeed, Inc.",                 "Parent",     ""),
    "siliconware precision industries co ltd": ("ASE Technology Holding Co., Ltd.","Acquired",  "Merged into ASE Technology; delisted 2018"),
    "imec vzw":                                ("imec",                            "Research institute","Belgium semiconductor R&D institute"),
    "siemens aktiengesellschaft":              ("Siemens AG",                      "Parent",     ""),
    "alibaba group holding limited":           ("Alibaba Group Holding Limited",   "Parent",     ""),
    "panasonic intellectual property management co ltd":("Panasonic Holdings Corporation","Subsidiary","Japan IP entity"),
    "imagination technologies limited":        ("Imagination Technologies Limited","Parent",     "Private; GPU IP"),
    "delta electronics inc":                   ("Delta Electronics, Inc.",         "Parent",     ""),
    "socionext inc":                           ("Socionext Inc.",                  "Parent",     ""),
    "lg electronics inc":                      ("LG Electronics Inc.",             "Parent",     ""),
    "marvell asia pte ltd":                    ("Marvell Technology, Inc.",        "Subsidiary", "Singapore entity"),
    "innolux corporation":                     ("Innolux Corporation",             "Parent",     ""),
    "stats chippac pte ltd":                   ("JCET Group Co., Ltd.",            "Acquired",   "Acquired by JCET 2015"),
    "kepler computing inc":                    ("Kepler Computing Inc.",           "Parent",     ""),
    "capital one services llc":                ("Capital One Financial Corporation","Subsidiary","Primary operating entity"),
    "mellanox technologies ltd":               ("Nvidia Corporation",              "Acquired",   "Acquired by Nvidia Apr 2020"),
    "rambus inc":                              ("Rambus Inc.",                     "Parent",     ""),
    "nxp usa inc":                             ("NXP Semiconductors N.V.",         "Subsidiary", "US entity"),
    "stmicroelectronics srl":                  ("STMicroelectronics N.V.",         "Subsidiary", "Italy entity"),
    "lodestar licensing group llc":            ("Lodestar Licensing Group LLC",    "Parent",     "IP licensing entity"),
    "amkor technology singapore holding pte ltd":("Amkor Technology, Inc.",        "Subsidiary", "Singapore holding entity"),
    "macronix international co ltd":           ("Macronix International Co., Ltd.","Parent",     ""),
    "sumitomo electric industries ltd":        ("Sumitomo Electric Industries, Ltd.","Parent",   ""),
    "bank of america corporation":             ("Bank of America Corporation",     "Parent",     ""),
    "softbank group corp":                     ("SoftBank Group Corp.",            "Parent",     ""),
    "murata manufacturing co ltd":             ("Murata Manufacturing Co., Ltd.",  "Parent",     ""),
    "nokia technologies oy":                   ("Nokia Corporation",               "Subsidiary", "Nokia IP licensing arm"),
    "tdk corporation":                         ("TDK Corporation",                 "Parent",     ""),
    "entegris inc":                            ("Entegris, Inc.",                  "Parent",     ""),
    "snap inc":                                ("Snap Inc.",                       "Parent",     ""),
    "seagate technology llc":                  ("Seagate Technology Holdings plc", "Subsidiary", "Operating entity"),
    "resonac corporation":                     ("Resonac Corporation",             "Parent",     ""),
    "analog devices inc":                      ("Analog Devices, Inc.",            "Parent",     ""),
    "paypal inc":                              ("PayPal Holdings, Inc.",            "Subsidiary", "Operating entity"),
    "gm global technology operations llc":     ("General Motors Company",          "Subsidiary", "R&D/IP entity"),
    "general electric company":                ("GE Aerospace",                    "Parent",     "GE split into 3 cos 2024; GE Aerospace is successor"),
    "honeywell international inc":             ("Honeywell International Inc.",    "Parent",     ""),
    "synopsys inc":                            ("Synopsys, Inc.",                  "Parent",     ""),
    "intuit inc":                              ("Intuit Inc.",                     "Parent",     ""),
    "tesla inc":                               ("Tesla, Inc.",                     "Parent",     ""),
    "pure storage inc":                        ("Pure Storage, Inc.",              "Parent",     ""),
    "snowflake inc":                           ("Snowflake Inc.",                  "Parent",     ""),
    "asml netherlands bv":                     ("ASML Holding N.V.",               "Subsidiary", "Netherlands operating entity"),
    "netapp inc":                              ("NetApp, Inc.",                    "Parent",     ""),
    "cadence design systems inc":              ("Cadence Design Systems, Inc.",    "Parent",     ""),
    "palantir technologies inc":               ("Palantir Technologies Inc.",      "Parent",     ""),
    "servicenow inc":                          ("ServiceNow, Inc.",                "Parent",     ""),
    "illumina inc":                            ("Illumina, Inc.",                  "Parent",     ""),
    "ebay inc":                                ("eBay Inc.",                       "Parent",     ""),
    "juniper networks inc":                    ("Juniper Networks, Inc.",          "Parent",     ""),
    "visa international service association":  ("Visa Inc.",                       "Subsidiary", "US operating entity"),
    "mastercard international incorporated":   ("Mastercard Incorporated",         "Subsidiary", "US operating entity"),
    "wells fargo bank na":                     ("Wells Fargo & Company",           "Subsidiary", "Primary banking entity"),
    "jpmorgan chase bank na":                  ("JPMorgan Chase & Co.",            "Subsidiary", "Primary banking entity"),
    "equifax inc":                             ("Equifax Inc.",                    "Parent",     ""),
    "palo alto networks inc":                  ("Palo Alto Networks, Inc.",        "Parent",     ""),
    "corning incorporated":                    ("Corning Incorporated",            "Parent",     ""),
    "kyndryl inc":                             ("Kyndryl Holdings, Inc.",          "Parent",     "Spun off from IBM Nov 2021"),
    "dropbox inc":                             ("Dropbox, Inc.",                   "Parent",     ""),
    "fair isaac corporation":                  ("Fair Isaac Corporation (FICO)",   "Parent",     ""),
    "ciena corporation":                       ("Ciena Corporation",               "Parent",     ""),
    "arista networks inc":                     ("Arista Networks, Inc.",           "Parent",     ""),
    "allegro microsystems llc":                ("Allegro MicroSystems, Inc.",      "Subsidiary", "Operating entity"),
    "power integrations inc":                  ("Power Integrations, Inc.",        "Parent",     ""),
    "silicon laboratories inc":                ("Silicon Laboratories Inc.",       "Parent",     ""),
    "skyworks solutions inc":                  ("Skyworks Solutions, Inc.",        "Parent",     ""),
    "macom technology solutions holdings inc": ("MACOM Technology Solutions Holdings, Inc.","Parent",""),
    "navitas semiconductor limited":           ("Navitas Semiconductor Limited",   "Parent",     ""),
    "monolithic power systems inc":            ("Monolithic Power Systems, Inc.",  "Parent",     ""),
    "maxim integrated products inc":           ("Analog Devices, Inc.",            "Acquired",   "Acquired by ADI Aug 2021"),
    "cypress semiconductor corporation":       ("Infineon Technologies AG",        "Acquired",   "Acquired by Infineon Apr 2020"),

    # Nvidia
    "nvidia corp":                             ("Nvidia Corporation",              "Duplicate",  "Name variant"),

    # Panasonic
    "panasonic intellectual property corporation of america":("Panasonic Holdings Corporation","Subsidiary","US IP entity"),

    # Analog Devices
    "analog devices international unlimited company":("Analog Devices, Inc.",      "Subsidiary", "Ireland holding entity"),

    # SanDisk (WD subsidiary; spun off as SanDisk Corp Feb 2024)
    "sandisk technologies inc":                ("SanDisk Corporation",             "Duplicate",  "Name variant"),

    # Uatc LLC (Uber ATG)
    "uatc llc":                                ("Uber Technologies, Inc.",         "Subsidiary", "Uber Advanced Technologies Group; sold to Aurora 2021"),

    # Qualcomm (already has company_name for parent, just adding QTI)
    # NEC already covered

    # EMC / Dell
    "emc ip holding company llc":              ("Dell Technologies Inc.",          "Subsidiary", "EMC IP – Dell subsidiary"),

    # Intel IP
    "intel ip corporation":                    ("Intel Corporation",               "Subsidiary", "Intel patent holding subsidiary"),

    # Mellanox → Nvidia
    "mellanox technologies ltd":               ("Nvidia Corporation",              "Acquired",   "Acquired by Nvidia Apr 2020"),

    # Xilinx → AMD
    "xilinx inc":                              ("Advanced Micro Devices, Inc.",    "Acquired",   "Acquired by AMD Feb 2022"),

    # ATI → AMD
    "ati technologies ulc":                    ("Advanced Micro Devices, Inc.",    "Acquired",   "Acquired by AMD Jul 2006"),

    # Red Hat → IBM
    "red hat inc":                             ("IBM Corporation",                 "Acquired",   "Acquired by IBM Jul 2019"),

    # Avago → Broadcom
    "avago technologies international sales pte limited": ("Broadcom Inc.",        "Predecessor","Avago acquired Broadcom 2016; renamed itself Broadcom Inc."),

    # DeepMind, X Dev, Waymo → Alphabet
    "deepmind technologies limited":           ("Alphabet Inc.",                   "Subsidiary", "AI research; acquired by Google 2014"),
    "x development llc":                       ("Alphabet Inc.",                   "Subsidiary", "Moonshot lab"),
    "waymo llc":                               ("Alphabet Inc.",                   "Subsidiary", "Autonomous vehicles"),
    "google llc":                              ("Alphabet Inc.",                   "Subsidiary", "Primary operating subsidiary"),

    # HP split (2015): HPE vs HP Inc.
    "hewlett packard enterprise development lp":("Hewlett Packard Enterprise Company","Subsidiary","HPE R&D entity"),
    "hewlettpackard development company lp":   ("HP Inc.",                         "Subsidiary", "HP Inc. R&D entity"),

    # Microsoft patent arm
    "microsoft technology licensing llc":      ("Microsoft Corporation",           "Subsidiary", "Patent licensing arm"),

    # AT&T IP entity
    "att intellectual property i lp":          ("AT&T Inc.",                       "Subsidiary", "IP licensing entity"),

    # Amazon patent entity
    "amazon technologies inc":                 ("Amazon.com, Inc.",                "Subsidiary", "Patent holding entity"),

    # onsemi
    "semiconductor components industries llc": ("onsemi (ON Semiconductor)",       "Subsidiary", "Primary operating entity"),
}

# ── Official names for known parents (used when company_name col is populated) ─
# Maps lowercase company_name → (official_name, entity_type, note)
OFFICIAL = {
    "taiwan semiconductor manufacturing company ltd":        ("Taiwan Semiconductor Manufacturing Company Limited","Parent",""),
    "globalfoundries inc":                                   ("GlobalFoundries Inc.",              "Parent",""),
    "infineon technologies ag":                              ("Infineon Technologies AG",           "Parent",""),
    "international business machines corporation":           ("IBM Corporation",                    "Parent",""),
    "intel corporation":                                     ("Intel Corporation",                  "Parent",""),
    "micron technology inc":                                 ("Micron Technology, Inc.",            "Parent",""),
    "google llc":                                            ("Alphabet Inc.",                      "Subsidiary","Primary operating subsidiary"),
    "applied materials inc":                                 ("Applied Materials, Inc.",            "Parent",""),
    "microsoft technology licensing llc":                    ("Microsoft Corporation",              "Subsidiary","Patent licensing arm"),
    "advanced micro devices inc":                            ("Advanced Micro Devices, Inc.",       "Parent",""),
    "amazon technologies inc":                               ("Amazon.com, Inc.",                   "Subsidiary","Patent holding entity"),
    "arm limited":                                           ("Arm Holdings plc",                   "Parent","Listed on Nasdaq Sep 2023"),
    "advanced semiconductor engineering inc":                ("ASE Technology Holding Co., Ltd.",   "Subsidiary","Primary operating entity"),
    "adobe inc":                                             ("Adobe Inc.",                         "Parent",""),
    "murata manufacturing co ltd":                           ("Murata Manufacturing Co., Ltd.",     "Parent",""),
    "toshiba electronic devices storage corporation":        ("Toshiba Corporation",               "Subsidiary","Storage/discrete devices"),
    "nvidia corporation":                                    ("Nvidia Corporation",                 "Parent",""),
    "yangtze memory technologies co ltd":                    ("Yangtze Memory Technologies Co., Ltd.","Parent",""),
    "apple inc":                                             ("Apple Inc.",                         "Parent",""),
    "tencent technology shenzhen company limited":           ("Tencent Holdings Limited",           "Subsidiary","Core tech entity"),
    "deepmind technologies limited":                         ("Alphabet Inc.",                      "Subsidiary","AI research; acquired 2014"),
    "daikin industries ltd":                                 ("Daikin Industries, Ltd.",            "Parent",""),
    "electronics and telecommunications research institute": ("ETRI (Electronics and Telecommunications Research Institute)","Research institute","South Korean gov't R&D"),
    "wolfspeed inc":                                         ("Wolfspeed, Inc.",                    "Parent",""),
    "monolithic 3d inc":                                     ("Monolithic 3D Inc.",                 "Parent",""),
    "telefonaktiebolaget lm ericsson publ":                  ("Ericsson",                           "Parent",""),
    "institute of microelectronics chinese academy of sciences":("Institute of Microelectronics, Chinese Academy of Sciences","Research institute",""),
    "accenture global solutions limited":                    ("Accenture plc",                      "Subsidiary","Ireland operating entity"),
    "vmware inc":                                            ("VMware LLC",                         "Predecessor","Acquired by Broadcom Nov 2023"),
    "microchip technology incorporated":                     ("Microchip Technology Incorporated",  "Parent",""),
    "diodes incorporated":                                   ("Diodes Incorporated",                "Parent",""),
    "meta platforms inc":                                    ("Meta Platforms, Inc.",               "Parent",""),
    "adeia semiconductor bonding technologies inc":          ("Adeia Inc.",                         "Parent",""),
    "montage technology co ltd":                             ("Montage Technology Co., Ltd.",       "Parent",""),
    "monolithic power systems inc":                          ("Monolithic Power Systems, Inc.",     "Parent",""),
    "alpha and omega semiconductor international lp":        ("Alpha and Omega Semiconductor Limited","Subsidiary","US LP entity"),
    "wuhan xinxin semiconductor manufacturing co ltd":       ("Wuhan Xinxin Semiconductor Manufacturing Co., Ltd.","Parent",""),
    "dwave systems inc":                                     ("D-Wave Systems Inc.",                "Parent",""),
    "etron technology inc":                                  ("Etron Technology, Inc.",             "Parent",""),
    "danfoss as":                                            ("Danfoss A/S",                        "Parent",""),
    "arista networks inc":                                   ("Arista Networks, Inc.",              "Parent",""),
    "csmc technologies fab2 co ltd":                         ("CSMC Technologies Fab2 Co., Ltd.",   "Parent",""),
    "copeland lp":                                           ("Copeland LP",                        "Parent","Spun off from Emerson Electric Feb 2023"),
    "avago technologies international sales pte limited":    ("Broadcom Inc.",                      "Predecessor","Avago → Broadcom rename 2016"),
    "cree inc":                                              ("Wolfspeed, Inc.",                    "Predecessor","Rebranded Oct 2021"),
    "ati technologies ulc":                                  ("Advanced Micro Devices, Inc.",       "Acquired","Acquired Jul 2006"),
    "xilinx inc":                                            ("Advanced Micro Devices, Inc.",       "Acquired","Acquired Feb 2022"),
    "globalfoundries singapore pte ltd":                     ("GlobalFoundries Inc.",               "Subsidiary","Singapore entity"),
    "deca technologies usa inc":                             ("Deca Technologies USA, Inc.",        "Parent",""),
    "facebook inc":                                          ("Meta Platforms, Inc.",               "Predecessor","Renamed Meta Oct 2021"),
    "eth zurich":                                            ("ETH Zurich",                         "University",""),
    "toshiba electronic devices storage corporation":        ("Toshiba Corporation",               "Subsidiary",""),
}


ETYPE_PRIORITY = {
    "Parent": 0, "Independent": 1, "Research institute": 2, "University": 3,
    "Acquired": 4, "Predecessor": 5, "Samsung subsidiary": 6,
    "Subsidiary": 7, "Former subsidiary": 8, "Duplicate": 9,
    "Grouped (source)": 10, "": 11,
}

def best_etype(a, b):
    return a if ETYPE_PRIORITY.get(a, 99) <= ETYPE_PRIORITY.get(b, 99) else b

def normalize(s):
    return s.strip().lower()


# ─── Build canonical lookup ───────────────────────────────────────────────────
# first_applicant (normalized) → (official_name, entity_type, note)
lookup = {}

# Load source data to also pick up company_name column mappings
with open(INPUT, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        fa  = normalize(row["first_applicant"])
        cn  = normalize(row["company_name"])
        if cn:
            if cn in OFFICIAL:
                official, etype, note = OFFICIAL[cn]
            else:
                # company_name exists but we don't have an OFFICIAL entry; title-case it
                official = row["company_name"].strip()
                etype    = "Grouped (source)"
                note     = ""
            lookup[fa] = (official, etype, note)

# Apply EXTRA overrides (may overwrite or add)
for fa_norm, val in EXTRA.items():
    lookup[fa_norm] = val

# ─── Aggregate ───────────────────────────────────────────────────────────────
from collections import defaultdict

groups = defaultdict(lambda: {"entity_type":"", "note":"",
                               "patents":0, "citations":0, "variants":[]})

with open(INPUT, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        fa      = row["first_applicant"].strip()
        fa_norm = normalize(fa)
        patents  = int(row["num_company_patents"]  or 0)
        citations= int(row["num_company_citations"] or 0)

        if fa_norm in lookup:
            official, etype, note = lookup[fa_norm]
        else:
            official = fa  # keep as-is
            etype    = ""
            note     = ""

        g = groups[official]
        g["entity_type"] = best_etype(g["entity_type"], etype)
        if not g["note"]:
            g["note"] = note
        g["patents"]    += patents
        g["citations"]  += citations
        g["variants"].append(fa)

# ─── Write output ────────────────────────────────────────────────────────────
with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["official_name", "entity_type", "total_patents",
                     "total_citations", "notes", "raw_name_variants"])
    for official, g in sorted(groups.items(), key=lambda x: -x[1]["patents"]):
        variants = "; ".join(sorted(set(g["variants"])))
        writer.writerow([official, g["entity_type"],
                         g["patents"], g["citations"], g["note"], variants])

total_in  = sum(g["patents"] for g in groups.values())
total_out = len(groups)
print(f"Input rows : 9463")
print(f"Output rows: {total_out}  (unique canonical companies)")
print(f"Total patents preserved: {total_in}")

# Show top merged groups
print("\nTop merged groups (>1 variant):")
merged = [(o, g) for o, g in groups.items() if len(set(g["variants"])) > 1]
for o, g in sorted(merged, key=lambda x: -x[1]["patents"])[:20]:
    n = len(set(g["variants"]))
    print(f"  {n} variants → {o!r}  ({g['patents']} patents)")
