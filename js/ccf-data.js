// js/ccf-data.js — CCF 第七版推荐国际学术会议和期刊目录 (2026)
// Source: 中国计算机学会推荐国际学术会议和期刊目录（2026年）

const CCF_DOMAINS = [
    "人工智能",
    "数据库/数据挖掘/内容检索",
    "计算机图形学与多媒体",
    "计算机科学理论",
    "软件工程/系统软件/程序设计语言",
    "计算机网络",
    "网络与信息安全",
    "计算机体系结构/并行与分布计算/存储系统",
    "人机交互与普适计算",
    "交叉/综合/新兴",
];

const CCF_CONFERENCES = [
    // ── 人工智能 ──────────────────────────────────────────────
    // A
    { venue: "AAAI",   tier: "A", domain: "人工智能" },
    { venue: "NeurIPS", tier: "A", domain: "人工智能" },
    { venue: "ACL",    tier: "A", domain: "人工智能" },
    { venue: "CVPR",   tier: "A", domain: "人工智能" },
    { venue: "ICCV",   tier: "A", domain: "人工智能" },
    { venue: "ICML",   tier: "A", domain: "人工智能" },
    { venue: "ICLR",   tier: "A", domain: "人工智能" },
    // B
    { venue: "COLT",   tier: "B", domain: "人工智能" },
    { venue: "EMNLP",  tier: "B", domain: "人工智能" },
    { venue: "ECAI",   tier: "B", domain: "人工智能" },
    { venue: "ECCV",   tier: "B", domain: "人工智能" },
    { venue: "ICRA",   tier: "B", domain: "人工智能" },
    { venue: "ICAPS",  tier: "B", domain: "人工智能" },
    { venue: "IJCAI",  tier: "B", domain: "人工智能" },
    { venue: "AAMAS",  tier: "B", domain: "人工智能" },
    { venue: "UAI",    tier: "B", domain: "人工智能" },
    { venue: "KR",     tier: "B", domain: "人工智能" },
    { venue: "NAACL",  tier: "B", domain: "人工智能" },
    { venue: "COLING", tier: "B", domain: "人工智能" },
    { venue: "IROS",   tier: "B", domain: "人工智能" },
    { venue: "MICCAI_conf", tier: "B", domain: "人工智能" },
    { venue: "Interspeech", tier: "B", domain: "人工智能" },
    // C
    { venue: "AISTATS", tier: "C", domain: "人工智能" },
    { venue: "ACCV",    tier: "C", domain: "人工智能" },
    { venue: "ACML",    tier: "C", domain: "人工智能" },
    { venue: "BMVC",    tier: "C", domain: "人工智能" },
    { venue: "NLPCC",   tier: "C", domain: "人工智能" },
    { venue: "GECCO",   tier: "C", domain: "人工智能" },
    { venue: "FG",      tier: "C", domain: "人工智能" },
    { venue: "ICPR",    tier: "C", domain: "人工智能" },
    { venue: "ICDAR",   tier: "C", domain: "人工智能" },
    { venue: "ICANN",   tier: "C", domain: "人工智能" },
    { venue: "ICONIP",  tier: "C", domain: "人工智能" },
    { venue: "CSCWD",   tier: "C", domain: "人工智能" },

    // ── 数据库/数据挖掘/内容检索 ──────────────────────────────
    // A
    { venue: "SIGMOD", tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SIGKDD", tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ICDE",   tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SIGIR",  tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "VLDB",   tier: "A", domain: "数据库/数据挖掘/内容检索" },
    // B
    { venue: "CIKM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "WSDM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "PODS",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "DASFAA", tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ECML-PKDD", tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "EDBT",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ICDM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "RecSys", tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SDM",    tier: "B", domain: "数据库/数据挖掘/内容检索" },
    // C
    { venue: "APWeb",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "DEXA",   tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ECIR",   tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ESWC",   tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "WebDB",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ER",     tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "MDM",    tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SSDBM",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "PAKDD",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SSDBM",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "WISE",   tier: "C", domain: "数据库/数据挖掘/内容检索" },

    // ── 计算机图形学与多媒体 ──────────────────────────────────
    // A
    { venue: "ACMMM",    tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "SIGGRAPH", tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "IEEEVIS",  tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "VR",       tier: "A", domain: "计算机图形学与多媒体" },
    // B
    { venue: "ICMR",        tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "I3D",         tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "SCA",         tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "DCC",         tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "Eurographics", tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "EuroVis",     tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ICASSP",      tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ICME",        tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ISMAR",       tier: "B", domain: "计算机图形学与多媒体" },
    // C
    { venue: "VRST",   tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "CASA",   tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "CGI",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "GMP",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "PacificVis", tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "3DV",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "ICIP",   tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "PG",     tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "CVM",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "PRCV",   tier: "C", domain: "计算机图形学与多媒体" },

    // ── 计算机科学理论 ────────────────────────────────────────
    // A
    { venue: "STOC", tier: "A", domain: "计算机科学理论" },
    { venue: "SODA", tier: "A", domain: "计算机科学理论" },
    { venue: "CAV",  tier: "A", domain: "计算机科学理论" },
    { venue: "FOCS", tier: "A", domain: "计算机科学理论" },
    { venue: "LICS", tier: "A", domain: "计算机科学理论" },
    // B
    { venue: "SoCG",  tier: "B", domain: "计算机科学理论" },
    { venue: "ESA",   tier: "B", domain: "计算机科学理论" },
    { venue: "CCC",   tier: "B", domain: "计算机科学理论" },
    { venue: "ICALP", tier: "B", domain: "计算机科学理论" },
    { venue: "CADE",  tier: "B", domain: "计算机科学理论" },
    { venue: "CONCUR", tier: "B", domain: "计算机科学理论" },
    { venue: "TACAS", tier: "B", domain: "计算机科学理论" },
    // C
    { venue: "CSL",   tier: "C", domain: "计算机科学理论" },
    { venue: "FSTTCS", tier: "C", domain: "计算机科学理论" },
    { venue: "DSAA",  tier: "C", domain: "计算机科学理论" },
    { venue: "ICTAC", tier: "C", domain: "计算机科学理论" },
    { venue: "IPCO",  tier: "C", domain: "计算机科学理论" },
    { venue: "MFCS",  tier: "C", domain: "计算机科学理论" },
    { venue: "RP",    tier: "C", domain: "计算机科学理论" },
    { venue: "SAT",   tier: "C", domain: "计算机科学理论" },

    // ── 软件工程/系统软件/程序设计语言 ────────────────────────
    // A
    { venue: "PLDI",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "POPL",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "FSE",    tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "SOSP",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "OOPSLA", tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ASE",    tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICSE",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ISSTA",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "OSDI",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "FM",     tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    // B
    { venue: "ECOOP",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ETAPS",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICPC",   tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "RE_conf", tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "CAiSE",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICFP",   tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "MSR",    tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICSME",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    // C
    { venue: "PEPM",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "PASTE",  tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "APLAS",  tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "APSEC",  tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "EASE",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ECSA",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "GPCE",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "SCAM",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "SLE",    tier: "C", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "SPIN",   tier: "C", domain: "软件工程/系统软件/程序设计语言" },

    // ── 计算机网络 ────────────────────────────────────────────
    // A
    { venue: "SIGCOMM", tier: "A", domain: "计算机网络" },
    { venue: "MobiCom", tier: "A", domain: "计算机网络" },
    { venue: "INFOCOM", tier: "A", domain: "计算机网络" },
    { venue: "NSDI",    tier: "A", domain: "计算机网络" },
    // B
    { venue: "SenSys",  tier: "B", domain: "计算机网络" },
    { venue: "CoNEXT",  tier: "B", domain: "计算机网络" },
    { venue: "SECON",   tier: "B", domain: "计算机网络" },
    { venue: "IPSN",    tier: "B", domain: "计算机网络" },
    { venue: "MobiSys", tier: "B", domain: "计算机网络" },
    { venue: "IMC",     tier: "B", domain: "计算机网络" },
    // C
    { venue: "ANCS",    tier: "C", domain: "计算机网络" },
    { venue: "APNOMS",  tier: "C", domain: "计算机网络" },
    { venue: "FORTE",   tier: "C", domain: "计算机网络" },
    { venue: "LCN",     tier: "C", domain: "计算机网络" },
    { venue: "GLOBECOM", tier: "C", domain: "计算机网络" },
    { venue: "ICC",     tier: "C", domain: "计算机网络" },
    { venue: "PAM",     tier: "C", domain: "计算机网络" },
    { venue: "WCNC",    tier: "C", domain: "计算机网络" },
    { venue: "WoWMoM",  tier: "C", domain: "计算机网络" },

    // ── 网络与信息安全 ────────────────────────────────────────
    // A
    { venue: "CCS",          tier: "A", domain: "网络与信息安全" },
    { venue: "EUROCRYPT",    tier: "A", domain: "网络与信息安全" },
    { venue: "S&P",          tier: "A", domain: "网络与信息安全" },
    { venue: "CRYPTO",       tier: "A", domain: "网络与信息安全" },
    { venue: "USENIXSecurity", tier: "A", domain: "网络与信息安全" },
    { venue: "NDSS",         tier: "A", domain: "网络与信息安全" },
    // B
    { venue: "ACSAC",    tier: "B", domain: "网络与信息安全" },
    { venue: "ASIACRYPT", tier: "B", domain: "网络与信息安全" },
    { venue: "ESORICS",   tier: "B", domain: "网络与信息安全" },
    { venue: "FSE_crypto", tier: "B", domain: "网络与信息安全" },
    { venue: "CSFW",     tier: "B", domain: "网络与信息安全" },
    { venue: "CHES",     tier: "B", domain: "网络与信息安全" },
    { venue: "AsiaCCS",  tier: "B", domain: "网络与信息安全" },
    { venue: "EuroS&P",  tier: "B", domain: "网络与信息安全" },
    // C
    { venue: "WiSec",   tier: "C", domain: "网络与信息安全" },
    { venue: "SACMAT",  tier: "C", domain: "网络与信息安全" },
    { venue: "DRM",     tier: "C", domain: "网络与信息安全" },
    { venue: "IHMSec",  tier: "C", domain: "网络与信息安全" },
    { venue: "ACNS",    tier: "C", domain: "网络与信息安全" },
    { venue: "AsiaCCS_C", tier: "C", domain: "网络与信息安全" },
    { venue: "ICDF2C", tier: "C", domain: "网络与信息安全" },
    { venue: "DIMVA",  tier: "C", domain: "网络与信息安全" },

    // ── 计算机体系结构/并行与分布计算/存储系统 ────────────────
    // A
    { venue: "PPoPP",  tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "FAST",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "DAC",    tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "HPCA",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "MICRO",  tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "SC",     tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ASPLOS", tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ISCA",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ATC",    tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "EuroSys", tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "HPDC",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    // B
    { venue: "SoCC",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "SPAA",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "PODC",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "FPGA",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "CGO",   tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "DATE",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ICCD",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ICDCS", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "IPDPS", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "PACT",  tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    // C
    { venue: "CF",     tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "SYSTOR", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "NOCS",   tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ASAP",   tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ASP-DAC", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ETS",    tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "GLSVLSI", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "HiPEAC", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ICS",    tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ISPASS", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ISSS",   tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统" },

    // ── 人机交互与普适计算 ────────────────────────────────────
    // A
    { venue: "CSCW",   tier: "A", domain: "人机交互与普适计算" },
    { venue: "CHI",    tier: "A", domain: "人机交互与普适计算" },
    { venue: "UbiComp", tier: "A", domain: "人机交互与普适计算" },
    { venue: "UIST",   tier: "A", domain: "人机交互与普适计算" },
    // B
    { venue: "GROUP",     tier: "B", domain: "人机交互与普适计算" },
    { venue: "IUI",       tier: "B", domain: "人机交互与普适计算" },
    { venue: "ISS",       tier: "B", domain: "人机交互与普适计算" },
    { venue: "ECSCW",     tier: "B", domain: "人机交互与普适计算" },
    { venue: "PERCOM",    tier: "B", domain: "人机交互与普适计算" },
    { venue: "MobileHCI", tier: "B", domain: "人机交互与普适计算" },
    { venue: "CHI_PLAY",  tier: "B", domain: "人机交互与普适计算" },
    // C
    { venue: "DIS",    tier: "C", domain: "人机交互与普适计算" },
    { venue: "ICMI",   tier: "C", domain: "人机交互与普适计算" },
    { venue: "ASSETS", tier: "C", domain: "人机交互与普适计算" },
    { venue: "GI",     tier: "C", domain: "人机交互与普适计算" },
    { venue: "UIC",    tier: "C", domain: "人机交互与普适计算" },
    { venue: "Haptics", tier: "C", domain: "人机交互与普适计算" },

    // ── 交叉/综合/新兴 ────────────────────────────────────────
    // A
    { venue: "WWW_conf", tier: "A", domain: "交叉/综合/新兴" },
    { venue: "RTSS", tier: "A", domain: "交叉/综合/新兴" },
    // B
    { venue: "CogSci",  tier: "B", domain: "交叉/综合/新兴" },
    { venue: "BIBM",    tier: "B", domain: "交叉/综合/新兴" },
    { venue: "EMSOFT",  tier: "B", domain: "交叉/综合/新兴" },
    { venue: "ISMB",    tier: "B", domain: "交叉/综合/新兴" },
    { venue: "RECOMB",  tier: "B", domain: "交叉/综合/新兴" },
    { venue: "MICCAI",  tier: "B", domain: "交叉/综合/新兴" },
    { venue: "IPSN_cross", tier: "B", domain: "交叉/综合/新兴" },
    // C
    { venue: "AMIA",       tier: "C", domain: "交叉/综合/新兴" },
    { venue: "APBC",       tier: "C", domain: "交叉/综合/新兴" },
    { venue: "IEEEBigData", tier: "C", domain: "交叉/综合/新兴" },
    { venue: "IEEECLOUD",  tier: "C", domain: "交叉/综合/新兴" },
    { venue: "SMC",        tier: "C", domain: "交叉/综合/新兴" },
    { venue: "COSIT",      tier: "C", domain: "交叉/综合/新兴" },
    { venue: "ICCPS",      tier: "C", domain: "交叉/综合/新兴" },
    { venue: "ITNG",       tier: "C", domain: "交叉/综合/新兴" },
];

// Build lookup map: venue → { tier, domain }
const CCF_CONF_MAP = {};
for (const c of CCF_CONFERENCES) {
    if (!CCF_CONF_MAP[c.venue]) {
        CCF_CONF_MAP[c.venue] = { tier: c.tier, domain: c.domain };
    }
}

const CCF_JOURNALS = [
    // ── 人工智能 ──────────────────────────────────────────────
    // A
    { abbr: "AI",     name: "Artificial Intelligence",           tier: "A", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "TPAMI",  name: "IEEE TPAMI",                        tier: "A", domain: "人工智能", publisher: "IEEE" },
    { abbr: "IJCV",   name: "International Journal of Computer Vision", tier: "A", domain: "人工智能", publisher: "Springer" },
    { abbr: "JMLR",   name: "Journal of Machine Learning Research", tier: "A", domain: "人工智能", publisher: "MIT Press" },
    // B
    { abbr: "TAP",    name: "ACM Trans. Applied Perception",     tier: "B", domain: "人工智能", publisher: "ACM" },
    { abbr: "AAMAS",  name: "Autonomous Agents and Multi-Agent Systems", tier: "B", domain: "人工智能", publisher: "Springer" },
    { abbr: "CL",     name: "Computational Linguistics",         tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "CVIU",   name: "Computer Vision and Image Understanding", tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "DKE",    name: "Data & Knowledge Engineering",      tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "EC",     name: "Evolutionary Computation",          tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "TAC",    name: "IEEE Trans. Affective Computing",   tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TASLP",  name: "IEEE TASLP",                        tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TCYB",   name: "IEEE Trans. Cybernetics",           tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TEC",    name: "IEEE Trans. Evolutionary Computation", tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TFS",    name: "IEEE Trans. Fuzzy Systems",         tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TNNLS",  name: "IEEE TNNLS",                        tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "IJAR",   name: "International J. Approximate Reasoning", tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "JAIR",   name: "J. Artificial Intelligence Research", tier: "B", domain: "人工智能", publisher: "AAAI" },
    { abbr: "PR",     name: "Pattern Recognition",               tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "TACL",   name: "Transactions of the ACL",           tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "ML",     name: "Machine Learning",                  tier: "B", domain: "人工智能", publisher: "Springer" },
    { abbr: "NeurComp", name: "Neural Computation",              tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "NN",     name: "Neural Networks",                   tier: "B", domain: "人工智能", publisher: "Elsevier" },
    // C
    { abbr: "TALLIP", name: "ACM Trans. Asian and Low-Resource Language Info. Processing", tier: "C", domain: "人工智能", publisher: "ACM" },
    { abbr: "APIN",   name: "Applied Intelligence",              tier: "C", domain: "人工智能", publisher: "Springer" },
    { abbr: "AIM",    name: "Artificial Intelligence in Medicine", tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "ALife",  name: "Artificial Life",                   tier: "C", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "CI",     name: "Computational Intelligence",        tier: "C", domain: "人工智能", publisher: "Wiley" },
    { abbr: "CSL",    name: "Computer Speech & Language",        tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "ConnSci", name: "Connection Science",              tier: "C", domain: "人工智能", publisher: "Taylor & Francis" },
    { abbr: "DSS",    name: "Decision Support Systems",          tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "EAAI",   name: "Engineering Applications of AI",    tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "ES",     name: "Expert Systems",                    tier: "C", domain: "人工智能", publisher: "Wiley" },
    { abbr: "ESWA",   name: "Expert Systems with Applications",  tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "FSS",    name: "Fuzzy Sets and Systems",            tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "TG",     name: "IEEE Trans. Games",                 tier: "C", domain: "人工智能", publisher: "IEEE" },
    { abbr: "IETCV",  name: "IET Computer Vision",               tier: "C", domain: "人工智能", publisher: "IET" },
    { abbr: "IETSP",  name: "IET Signal Processing",             tier: "C", domain: "人工智能", publisher: "IET" },
    { abbr: "KBS",    name: "Knowledge-Based Systems",           tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "Neurocomp", name: "Neurocomputing",                tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "PRL",    name: "Pattern Recognition Letters",       tier: "C", domain: "人工智能", publisher: "Elsevier" },

    // ── 数据库/数据挖掘/内容检索 ──────────────────────────────
    // A
    { abbr: "TODS",   name: "ACM TODS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TOIS",   name: "ACM TOIS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TKDE",   name: "IEEE TKDE",                         tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "IEEE" },
    { abbr: "VLDBJ",  name: "The VLDB Journal",                  tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    // B
    { abbr: "TKDD",   name: "ACM TKDD",                          tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TWEB",   name: "ACM Trans. the Web",                tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "AEI",    name: "Advanced Engineering Informatics",  tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "DKE_DB", name: "Data & Knowledge Engineering",      tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "DMKD",   name: "Data Mining and Knowledge Discovery", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "EJIS",   name: "European J. Information Systems",   tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "GeoInf", name: "GeoInformatica",                    tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "IPM",    name: "Information Processing & Management", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "ISci",   name: "Information Sciences",              tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "IS",     name: "Information Systems",               tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "JASIST", name: "J. Assoc. Information Science and Technology", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Wiley" },
    { abbr: "JWS",    name: "Journal of Web Semantics",          tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "KAIS",   name: "Knowledge and Information Systems",  tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "DSE",    name: "Data Science and Engineering",      tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    // C
    { abbr: "DPD",    name: "Distributed and Parallel Databases", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "IandM",  name: "Information & Management",          tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "IPL",    name: "Information Processing Letters",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "DiscComp", name: "Discover Computing",             tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "IJCIS",  name: "International J. Cooperative Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "World Scientific" },
    { abbr: "IJGIS",  name: "International J. Geographical Information Science", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Taylor & Francis" },
    { abbr: "IJIS",   name: "International J. Intelligent Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Wiley" },
    { abbr: "IJKM",   name: "International J. Knowledge Management", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI" },
    { abbr: "IJSWIS", name: "International J. Semantic Web and Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI" },
    { abbr: "JCIS",   name: "Journal of Computer Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IACIS" },
    { abbr: "JDM",    name: "Journal of Database Management",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI-Global" },
    { abbr: "JGITM",  name: "Journal of Global Information Technology Management", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Ivy League Publishing" },
    { abbr: "JIIS",   name: "Journal of Intelligent Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "JSIS",   name: "J. Strategic Information Systems",  tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "TIST",   name: "ACM Trans. Intelligent Systems and Technology", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TORS",   name: "ACM Trans. Recommender Systems",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },

    // ── 计算机图形学与多媒体 ──────────────────────────────────
    // A
    { abbr: "TOG",    name: "ACM Trans. on Graphics",            tier: "A", domain: "计算机图形学与多媒体", publisher: "ACM" },
    { abbr: "TIP",    name: "IEEE TIP",                          tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "TVCG",   name: "IEEE TVCG",                         tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "TMM",    name: "IEEE Trans. Multimedia",            tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    // B
    { abbr: "TOMM",   name: "ACM TOMM",                          tier: "B", domain: "计算机图形学与多媒体", publisher: "ACM" },
    { abbr: "CAGD",   name: "Computer Aided Geometric Design",   tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "CGF",    name: "Computer Graphics Forum",           tier: "B", domain: "计算机图形学与多媒体", publisher: "Wiley" },
    { abbr: "CAD",    name: "Computer-Aided Design",             tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "TCSVT",  name: "IEEE TCSVT",                        tier: "B", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "JASA",   name: "J. the Acoustical Society of America", tier: "B", domain: "计算机图形学与多媒体", publisher: "AIP" },
    { abbr: "SIIMS",  name: "SIAM J. Imaging Sciences",          tier: "B", domain: "计算机图形学与多媒体", publisher: "SIAM" },
    { abbr: "SPECOM", name: "Speech Communication",              tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "CVMJ",   name: "Computational Visual Media",        tier: "B", domain: "计算机图形学与多媒体", publisher: "Springer" },
    // C
    { abbr: "CGTA",   name: "Computational Geometry: Theory and Applications", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "CAVW",   name: "Computer Animation and Virtual Worlds", tier: "C", domain: "计算机图形学与多媒体", publisher: "Wiley" },
    { abbr: "CandG",  name: "Computers & Graphics",              tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "DCG",    name: "Discrete & Computational Geometry",  tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer" },
    { abbr: "SPL",    name: "IEEE Signal Processing Letters",    tier: "C", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "IETIPR", name: "IET Image Processing",              tier: "C", domain: "计算机图形学与多媒体", publisher: "IET" },
    { abbr: "JVCIR",  name: "J. Visual Communication and Image Representation", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "MS",     name: "Multimedia Systems",                tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer" },
    { abbr: "MTA",    name: "Multimedia Tools and Applications",  tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer" },
    { abbr: "SIGPRO", name: "Signal Processing",                 tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "SPIC",   name: "Signal Processing: Image Communication", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },
    { abbr: "TVC",    name: "The Visual Computer",               tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer" },
    { abbr: "VI",     name: "Visual Informatics",                tier: "C", domain: "计算机图形学与多媒体", publisher: "浙江大学" },
    { abbr: "VRIH",   name: "Virtual Reality & Intelligent Hardware", tier: "C", domain: "计算机图形学与多媒体", publisher: "北京航空航天大学" },
    { abbr: "GMOD",   name: "Graphical Models",                  tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier" },

    // ── 计算机科学理论 ────────────────────────────────────────
    // A
    { abbr: "TIT",    name: "IEEE Trans. Information Theory",    tier: "A", domain: "计算机科学理论", publisher: "IEEE" },
    { abbr: "IANDC",  name: "Information and Computation",       tier: "A", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "SICOMP", name: "SIAM J. Computing",                 tier: "A", domain: "计算机科学理论", publisher: "SIAM" },
    // B
    { abbr: "TALG",   name: "ACM Trans. Algorithms",             tier: "B", domain: "计算机科学理论", publisher: "ACM" },
    { abbr: "TOCL",   name: "ACM Trans. Computational Logic",    tier: "B", domain: "计算机科学理论", publisher: "ACM" },
    { abbr: "TOMS",   name: "ACM Trans. Mathematical Software",  tier: "B", domain: "计算机科学理论", publisher: "ACM" },
    { abbr: "Algor",  name: "Algorithmica",                      tier: "B", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "CC",     name: "Computational Complexity",          tier: "B", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "FAC",    name: "Formal Aspects of Computing",       tier: "B", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "FMSD",   name: "Formal Methods in System Design",   tier: "B", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "INFORMS", name: "INFORMS J. Computing",            tier: "B", domain: "计算机科学理论", publisher: "INFORMS" },
    { abbr: "JCSS",   name: "J. Computer and System Sciences",   tier: "B", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "JGO",    name: "J. Global Optimization",            tier: "B", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "JSC",    name: "J. Symbolic Computation",           tier: "B", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "MSCS",   name: "Mathematical Structures in Computer Science", tier: "B", domain: "计算机科学理论", publisher: "Cambridge" },
    { abbr: "TCS",    name: "Theoretical Computer Science",      tier: "B", domain: "计算机科学理论", publisher: "Elsevier" },
    // C
    { abbr: "ACTA",   name: "Acta Informatica",                  tier: "C", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "APAL",   name: "Annals of Pure and Applied Logic",   tier: "C", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "DAM",    name: "Discrete Applied Mathematics",      tier: "C", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "FUIN",   name: "Fundamenta Informaticae",           tier: "C", domain: "计算机科学理论", publisher: "IOS Press" },
    { abbr: "IPL_T",  name: "Information Processing Letters (Theory)", tier: "C", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "JCOMPL", name: "Journal of Complexity",             tier: "C", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "LOGCOM", name: "J. Logic and Computation",          tier: "C", domain: "计算机科学理论", publisher: "Oxford" },
    { abbr: "JSL",    name: "J. Symbolic Logic",                 tier: "C", domain: "计算机科学理论", publisher: "ASL" },
    { abbr: "LMCS",   name: "Logical Methods in Computer Science", tier: "C", domain: "计算机科学理论", publisher: "LMCS" },
    { abbr: "SIDMA",  name: "SIAM J. Discrete Mathematics",      tier: "C", domain: "计算机科学理论", publisher: "SIAM" },
    { abbr: "ToCS",   name: "Theory of Computing Systems",       tier: "C", domain: "计算机科学理论", publisher: "Springer" },
    { abbr: "TQC",    name: "ACM Trans. Quantum Computing",      tier: "C", domain: "计算机科学理论", publisher: "ACM" },

    // ── 软件工程/系统软件/程序设计语言 ────────────────────────
    // A
    { abbr: "TOPLAS", name: "ACM TOPLAS",                        tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM" },
    { abbr: "TOSEM",  name: "ACM TOSEM",                         tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM" },
    { abbr: "TSE",    name: "IEEE TSE",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE" },
    { abbr: "TSC",    name: "IEEE TSC",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE" },
    // B
    { abbr: "ASE_J",  name: "Automated Software Engineering",    tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "ESE",    name: "Empirical Software Engineering",    tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "IETS",   name: "IET Software",                      tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "IET" },
    { abbr: "IST",    name: "Information and Software Technology", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "JFP",    name: "Journal of Functional Programming",  tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Cambridge" },
    { abbr: "JSEP",   name: "Journal of Software: Evolution and Process", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley" },
    { abbr: "JSS",    name: "J. Systems and Software",           tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "RE",     name: "Requirements Engineering",          tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "SCP",    name: "Science of Computer Programming",   tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "SoSyM",  name: "Software and Systems Modeling",     tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "STVR",   name: "Software Testing, Verification and Reliability", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley" },
    { abbr: "SPE",    name: "Software: Practice and Experience",  tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley" },
    // C
    { abbr: "CL_J",   name: "Computer Languages, Systems & Structures", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "IJSEKE", name: "International J. Software Engineering and Knowledge Engineering", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "World Scientific" },
    { abbr: "STTT",   name: "International J. Software Tools for Technology Transfer", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "JLAMP",  name: "J. Logical and Algebraic Methods in Programming", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "JWE",    name: "Journal of Web Engineering",        tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Rinton Press" },
    { abbr: "SOCA",   name: "Service Oriented Computing and Applications", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "SQJ",    name: "Software Quality Journal",          tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "TPLP",   name: "Theory and Practice of Logic Programming", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Cambridge" },
    { abbr: "PACMPL", name: "Proceedings of the ACM on Programming Languages", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM" },

    // ── 计算机网络 ────────────────────────────────────────────
    // A
    { abbr: "JSAC",   name: "IEEE J. Selected Areas in Communications", tier: "A", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "TMC",    name: "IEEE Trans. Mobile Computing",      tier: "A", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "TON",    name: "IEEE/ACM Trans. Networking",        tier: "A", domain: "计算机网络", publisher: "IEEE" },
    // B
    { abbr: "TOIT",   name: "ACM Trans. Internet Technology",    tier: "B", domain: "计算机网络", publisher: "ACM" },
    { abbr: "TOSN",   name: "ACM Trans. Sensor Networks",        tier: "B", domain: "计算机网络", publisher: "ACM" },
    { abbr: "CN",     name: "Computer Networks",                 tier: "B", domain: "计算机网络", publisher: "Elsevier" },
    { abbr: "TCOMM",  name: "IEEE Trans. Communications",        tier: "B", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "TWC",    name: "IEEE Trans. Wireless Communications", tier: "B", domain: "计算机网络", publisher: "IEEE" },
    // C
    { abbr: "AdHoc",  name: "Ad Hoc Networks",                   tier: "C", domain: "计算机网络", publisher: "Elsevier" },
    { abbr: "ComCom", name: "Computer Communications",           tier: "C", domain: "计算机网络", publisher: "Elsevier" },
    { abbr: "TNSM",   name: "IEEE Trans. Network and Service Management", tier: "C", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "IETComm", name: "IET Communications",              tier: "C", domain: "计算机网络", publisher: "IET" },
    { abbr: "JNCA",   name: "J. Network and Computer Applications", tier: "C", domain: "计算机网络", publisher: "Elsevier" },
    { abbr: "MONET",  name: "Mobile Networks and Applications",   tier: "C", domain: "计算机网络", publisher: "Springer" },
    { abbr: "Networks", name: "Networks",                        tier: "C", domain: "计算机网络", publisher: "Wiley" },
    { abbr: "PPNA",   name: "Peer-to-Peer Networking and Applications", tier: "C", domain: "计算机网络", publisher: "Springer" },
    { abbr: "WCMC",   name: "Wireless Communications and Mobile Computing", tier: "C", domain: "计算机网络", publisher: "Wiley" },
    { abbr: "WiNet",  name: "Wireless Networks",                 tier: "C", domain: "计算机网络", publisher: "Springer" },
    { abbr: "IOT",    name: "IEEE Internet of Things Journal",   tier: "C", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "TIOT",   name: "ACM Trans. Internet of Things",     tier: "C", domain: "计算机网络", publisher: "ACM" },

    // ── 网络与信息安全 ────────────────────────────────────────
    // A
    { abbr: "TDSC",   name: "IEEE TDSC",                         tier: "A", domain: "网络与信息安全", publisher: "IEEE" },
    { abbr: "TIFS",   name: "IEEE TIFS",                         tier: "A", domain: "网络与信息安全", publisher: "IEEE" },
    { abbr: "JOC",    name: "Journal of Cryptology",             tier: "A", domain: "网络与信息安全", publisher: "Springer" },
    // B
    { abbr: "TOPS",   name: "ACM Trans. Privacy and Security",   tier: "B", domain: "网络与信息安全", publisher: "ACM" },
    { abbr: "CompSec", name: "Computers & Security",             tier: "B", domain: "网络与信息安全", publisher: "Elsevier" },
    { abbr: "DCC",    name: "Designs, Codes and Cryptography",   tier: "B", domain: "网络与信息安全", publisher: "Springer" },
    { abbr: "JCS",    name: "J. Computer Security",              tier: "B", domain: "网络与信息安全", publisher: "IOS Press" },
    { abbr: "Cybersec", name: "Cybersecurity",                   tier: "B", domain: "网络与信息安全", publisher: "Springer" },
    // C
    { abbr: "CLSR",   name: "Computer Law & Security Review",    tier: "C", domain: "网络与信息安全", publisher: "Elsevier" },
    { abbr: "EJISec", name: "EURASIP J. Information Security",   tier: "C", domain: "网络与信息安全", publisher: "Springer" },
    { abbr: "IETIFS", name: "IET Information Security",           tier: "C", domain: "网络与信息安全", publisher: "IET" },
    { abbr: "IMCS",   name: "Information and Computer Security",  tier: "C", domain: "网络与信息安全", publisher: "Emerald" },
    { abbr: "IJICS",  name: "International J. Information and Computer Security", tier: "C", domain: "网络与信息安全", publisher: "Inderscience" },
    { abbr: "IJISP",  name: "International J. Information Security and Privacy", tier: "C", domain: "网络与信息安全", publisher: "IGI Global" },
    { abbr: "JISA",   name: "J. Information Security and Applications", tier: "C", domain: "网络与信息安全", publisher: "Elsevier" },
    { abbr: "SCN",    name: "Security and Communication Networks", tier: "C", domain: "网络与信息安全", publisher: "Wiley" },
    { abbr: "HCC",    name: "High-Confidence Computing",         tier: "C", domain: "网络与信息安全", publisher: "Elsevier" },

    // ── 计算机体系结构/并行与分布计算/存储系统 ────────────────
    // A
    { abbr: "TOCS",   name: "ACM Trans. Computer Systems",       tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TOS",    name: "ACM Trans. Storage",                tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TCAD",   name: "IEEE TCAD",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "TC",     name: "IEEE Trans. Computers",             tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "TPDS",   name: "IEEE TPDS",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "TACO",   name: "ACM Trans. Architecture and Code Optimization", tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    // B
    { abbr: "TAAS",   name: "ACM Trans. Autonomous and Adaptive Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TODAES", name: "ACM Trans. Design Automation of Electronic Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TECS",   name: "ACM Trans. Embedded Computing Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TRETS",  name: "ACM Trans. Reconfigurable Technology and Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "TVLSI",  name: "IEEE Trans. VLSI Systems",          tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "JPDC",   name: "J. Parallel and Distributed Computing", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "JSA",    name: "J. Systems Architecture",           tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "ParComp", name: "Parallel Computing",              tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "PEval",  name: "Performance Evaluation",            tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "TCC",    name: "IEEE Trans. Cloud Computing",       tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    // C
    { abbr: "JETC",   name: "ACM J. Emerging Technologies in Computing Systems", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM" },
    { abbr: "Concurr", name: "Concurrency and Computation: Practice and Experience", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Wiley" },
    { abbr: "DC",     name: "Distributed Computing",             tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer" },
    { abbr: "FGCS",   name: "Future Generation Computer Systems", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "Integr",  name: "Integration, the VLSI Journal",   tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },
    { abbr: "JETTA",  name: "J. Electronic Testing",             tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer" },
    { abbr: "JGC",    name: "Journal of Grid Computing",         tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer" },
    { abbr: "RTS",    name: "Real-Time Systems",                 tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer" },
    { abbr: "TJSC",   name: "The Journal of Supercomputing",     tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer" },
    { abbr: "TCASI",  name: "IEEE Trans. Circuits and Systems I", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "THPC",   name: "CCF Trans. High Performance Computing", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "CCF" },
    { abbr: "TSUSC",  name: "IEEE Trans. Sustainable Computing",  tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },

    // ── 人机交互与普适计算 ────────────────────────────────────
    // A
    { abbr: "TOCHI",  name: "ACM TOCHI",                         tier: "A", domain: "人机交互与普适计算", publisher: "ACM" },
    { abbr: "IJHCS",  name: "Int. J. Human-Computer Studies",    tier: "A", domain: "人机交互与普适计算", publisher: "Elsevier" },
    // B
    { abbr: "CSCW_J", name: "Computer Supported Cooperative Work", tier: "B", domain: "人机交互与普适计算", publisher: "Springer" },
    { abbr: "HCI",    name: "Human-Computer Interaction",        tier: "B", domain: "人机交互与普适计算", publisher: "Taylor & Francis" },
    { abbr: "THMS",   name: "IEEE Trans. Human-Machine Systems", tier: "B", domain: "人机交互与普适计算", publisher: "IEEE" },
    { abbr: "IWC",    name: "Interacting with Computers",        tier: "B", domain: "人机交互与普适计算", publisher: "Oxford" },
    { abbr: "IJHCI",  name: "International J. Human-Computer Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Taylor & Francis" },
    { abbr: "UMUAI",  name: "User Modeling and User-Adapted Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Springer" },
    { abbr: "TSMC",   name: "IEEE Trans. Systems, Man, and Cybernetics: Systems", tier: "B", domain: "人机交互与普适计算", publisher: "IEEE" },
    { abbr: "TPCI",   name: "CCF Trans. Pervasive Computing and Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Springer" },
    // C
    { abbr: "BIT",    name: "Behaviour & Information Technology", tier: "C", domain: "人机交互与普适计算", publisher: "Taylor & Francis" },
    { abbr: "PUC",    name: "Personal and Ubiquitous Computing",  tier: "C", domain: "人机交互与普适计算", publisher: "Springer" },
    { abbr: "PMC",    name: "Pervasive and Mobile Computing",    tier: "C", domain: "人机交互与普适计算", publisher: "Elsevier" },
    { abbr: "PACMHCI", name: "Proceedings of the ACM on Human-Computer Interaction", tier: "C", domain: "人机交互与普适计算", publisher: "ACM" },
    { abbr: "THRI",   name: "ACM Trans. Human-Robot Interaction", tier: "C", domain: "人机交互与普适计算", publisher: "ACM" },

    // ── 交叉/综合/新兴 ────────────────────────────────────────
    // A
    { abbr: "JACM",   name: "Journal of the ACM",                tier: "A", domain: "交叉/综合/新兴", publisher: "ACM" },
    { abbr: "ProcIEEE", name: "Proceedings of the IEEE",         tier: "A", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "SCIS",   name: "Science China Information Sciences", tier: "A", domain: "交叉/综合/新兴", publisher: "Springer" },
    { abbr: "Bioinf", name: "Bioinformatics",                    tier: "A", domain: "交叉/综合/新兴", publisher: "Oxford" },
    // B
    { abbr: "BriefBio", name: "Briefings in Bioinformatics",    tier: "B", domain: "交叉/综合/新兴", publisher: "Oxford" },
    { abbr: "Cognition", name: "Cognition",                     tier: "B", domain: "交叉/综合/新兴", publisher: "Elsevier" },
    { abbr: "TASE",   name: "IEEE Trans. Automation Science and Engineering", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TGRS",   name: "IEEE Trans. Geoscience and Remote Sensing", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TITS",   name: "IEEE Trans. Intelligent Transportation Systems", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TMI",    name: "IEEE Trans. Medical Imaging",       tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TR",     name: "IEEE Trans. Robotics",              tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TCBB",   name: "IEEE/ACM TCBB",                     tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE/ACM" },
    { abbr: "JCST",   name: "J. Computer Science and Technology", tier: "B", domain: "交叉/综合/新兴", publisher: "Springer" },
    { abbr: "JAMIA",  name: "J. American Medical Informatics Association", tier: "B", domain: "交叉/综合/新兴", publisher: "BMJ" },
    { abbr: "PLOSCB", name: "PLOS Computational Biology",       tier: "B", domain: "交叉/综合/新兴", publisher: "PLOS" },
    { abbr: "CompJ",  name: "The Computer Journal",              tier: "B", domain: "交叉/综合/新兴", publisher: "Oxford" },
    { abbr: "WWW_J",  name: "World Wide Web",                   tier: "B", domain: "交叉/综合/新兴", publisher: "Springer" },
    { abbr: "FCS",    name: "Frontiers of Computer Science",     tier: "B", domain: "交叉/综合/新兴", publisher: "Springer" },
    { abbr: "BCRA",   name: "Blockchain: Research and Applications", tier: "B", domain: "交叉/综合/新兴", publisher: "Elsevier" },
    // C
    { abbr: "BMCBio", name: "BMC Bioinformatics",                tier: "C", domain: "交叉/综合/新兴", publisher: "BioMed Central" },
    { abbr: "CybSys", name: "Cybernetics and Systems",           tier: "C", domain: "交叉/综合/新兴", publisher: "Taylor & Francis" },
    { abbr: "GRSL",   name: "IEEE Geoscience and Remote Sensing Letters", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "JBHI",   name: "IEEE J. Biomedical and Health Informatics", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TBD",    name: "IEEE Trans. Big Data",              tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "IETITS", name: "IET Intelligent Transport Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "IET" },
    { abbr: "JBI",    name: "J. Biomedical Informatics",         tier: "C", domain: "交叉/综合/新兴", publisher: "Elsevier" },
    { abbr: "MedIA",  name: "Medical Image Analysis",            tier: "C", domain: "交叉/综合/新兴", publisher: "Elsevier" },
    { abbr: "TII",    name: "IEEE Trans. Industrial Informatics", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TCPS",   name: "ACM Trans. Cyber-Physical Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM" },
    { abbr: "TOCE",   name: "ACM Trans. Computing Education",    tier: "C", domain: "交叉/综合/新兴", publisher: "ACM" },
    { abbr: "EITEE",  name: "Engineering IT & Electronic Engineering", tier: "C", domain: "交叉/综合/新兴", publisher: "浙江大学" },
    { abbr: "TCSS",   name: "IEEE Trans. Computational Social Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TRel",   name: "IEEE Trans. Reliability",           tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "HEALTH", name: "ACM Trans. Computing for Healthcare", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM" },
    { abbr: "ACMDLT", name: "ACM Distributed Ledger Technologies", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM" },
];

// Build lookup map: abbr → { tier, domain, name, publisher }
const CCF_JOURNAL_MAP = {};
for (const j of CCF_JOURNALS) {
    CCF_JOURNAL_MAP[j.abbr] = { tier: j.tier, domain: j.domain, name: j.name, publisher: j.publisher };
}

// CCF tier badge color
function ccfTierClass(tier) {
    return tier === "A" ? "ccf-a" : tier === "B" ? "ccf-b" : "ccf-c";
}

function ccfTierLabel(tier) {
    return `CCF-${tier}`;
}
