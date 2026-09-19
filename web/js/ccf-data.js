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
    { abbr: "AI",     name: "Artificial Intelligence",           tier: "A", domain: "人工智能", publisher: "Elsevier", issn: "0004-3702" },
    { abbr: "TPAMI",  name: "IEEE TPAMI",                        tier: "A", domain: "人工智能", publisher: "IEEE", issn: "0162-8828" },
    { abbr: "IJCV",   name: "International Journal of Computer Vision", tier: "A", domain: "人工智能", publisher: "Springer", issn: "0920-5691" },
    { abbr: "JMLR",   name: "Journal of Machine Learning Research", tier: "A", domain: "人工智能", publisher: "MIT Press", issn: "1532-4435" },
    // B
    { abbr: "TAP",    name: "ACM Trans. Applied Perception",     tier: "B", domain: "人工智能", publisher: "ACM", issn: "1544-3558" },
    { abbr: "AAMAS",  name: "Autonomous Agents and Multi-Agent Systems", tier: "B", domain: "人工智能", publisher: "Springer", issn: "1387-2532" },
    { abbr: "CL",     name: "Computational Linguistics",         tier: "B", domain: "人工智能", publisher: "MIT Press", issn: "0891-2017" },
    { abbr: "CVIU",   name: "Computer Vision and Image Understanding", tier: "B", domain: "人工智能", publisher: "Elsevier", issn: "1077-3142" },
    { abbr: "DKE",    name: "Data & Knowledge Engineering",      tier: "B", domain: "人工智能", publisher: "Elsevier", issn: "0169-023X" },
    { abbr: "EC",     name: "Evolutionary Computation",          tier: "B", domain: "人工智能", publisher: "MIT Press", issn: "1063-6560" },
    { abbr: "TAC",    name: "IEEE Trans. Affective Computing",   tier: "B", domain: "人工智能", publisher: "IEEE", issn: "1949-3045" },
    { abbr: "TASLP",  name: "IEEE TASLP",                        tier: "B", domain: "人工智能", publisher: "IEEE", issn: "2329-9290" },
    { abbr: "TCYB",   name: "IEEE Trans. Cybernetics",           tier: "B", domain: "人工智能", publisher: "IEEE", issn: "2168-2267" },
    { abbr: "TEC",    name: "IEEE Trans. Evolutionary Computation", tier: "B", domain: "人工智能", publisher: "IEEE", issn: "1089-778X" },
    { abbr: "TFS",    name: "IEEE Trans. Fuzzy Systems",         tier: "B", domain: "人工智能", publisher: "IEEE", issn: "1063-6706" },
    { abbr: "TNNLS",  name: "IEEE TNNLS",                        tier: "B", domain: "人工智能", publisher: "IEEE", issn: "2162-2388" },
    { abbr: "IJAR",   name: "International J. Approximate Reasoning", tier: "B", domain: "人工智能", publisher: "Elsevier", issn: "0888-613X" },
    { abbr: "JAIR",   name: "J. Artificial Intelligence Research", tier: "B", domain: "人工智能", publisher: "AAAI", issn: "1076-9757" },
    { abbr: "PR",     name: "Pattern Recognition",               tier: "B", domain: "人工智能", publisher: "Elsevier", issn: "0031-3203" },
    { abbr: "TACL",   name: "Transactions of the ACL",           tier: "B", domain: "人工智能", publisher: "MIT Press", issn: "2306-3839" },
    { abbr: "ML",     name: "Machine Learning",                  tier: "B", domain: "人工智能", publisher: "Springer", issn: "0885-6125" },
    { abbr: "NeurComp", name: "Neural Computation",              tier: "B", domain: "人工智能", publisher: "MIT Press", issn: "0899-7667" },
    { abbr: "NN",     name: "Neural Networks",                   tier: "B", domain: "人工智能", publisher: "Elsevier", issn: "0893-6080" },
    // C
    { abbr: "TALLIP", name: "ACM Trans. Asian and Low-Resource Language Info. Processing", tier: "C", domain: "人工智能", publisher: "ACM", issn: "2375-4699" },
    { abbr: "APIN",   name: "Applied Intelligence",              tier: "C", domain: "人工智能", publisher: "Springer", issn: "0924-669X" },
    { abbr: "AIM",    name: "Artificial Intelligence in Medicine", tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0933-3657" },
    { abbr: "ALife",  name: "Artificial Life",                   tier: "C", domain: "人工智能", publisher: "MIT Press", issn: "1064-5462" },
    { abbr: "CI",     name: "Computational Intelligence",        tier: "C", domain: "人工智能", publisher: "Wiley", issn: "0824-7935" },
    { abbr: "CSL",    name: "Computer Speech & Language",        tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0885-2308" },
    { abbr: "ConnSci", name: "Connection Science",              tier: "C", domain: "人工智能", publisher: "Taylor & Francis", issn: "0954-0091" },
    { abbr: "DSS",    name: "Decision Support Systems",          tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0167-9236" },
    { abbr: "EAAI",   name: "Engineering Applications of AI",    tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0952-1976" },
    { abbr: "ES",     name: "Expert Systems",                    tier: "C", domain: "人工智能", publisher: "Wiley", issn: "0266-4720" },
    { abbr: "ESWA",   name: "Expert Systems with Applications",  tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0957-4174" },
    { abbr: "FSS",    name: "Fuzzy Sets and Systems",            tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0165-0114" },
    { abbr: "TG",     name: "IEEE Trans. Games",                 tier: "C", domain: "人工智能", publisher: "IEEE", issn: "2475-1502" },
    { abbr: "IETCV",  name: "IET Computer Vision",               tier: "C", domain: "人工智能", publisher: "IET", issn: "1751-9632" },
    { abbr: "IETSP",  name: "IET Signal Processing",             tier: "C", domain: "人工智能", publisher: "IET", issn: "1751-9675" },
    { abbr: "KBS",    name: "Knowledge-Based Systems",           tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0950-7051" },
    { abbr: "Neurocomp", name: "Neurocomputing",                tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0925-2312" },
    { abbr: "PRL",    name: "Pattern Recognition Letters",       tier: "C", domain: "人工智能", publisher: "Elsevier", issn: "0167-8655" },

    // ── 数据库/数据挖掘/内容检索 ──────────────────────────────
    // A
    { abbr: "TODS",   name: "ACM TODS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "0362-5915" },
    { abbr: "TOIS",   name: "ACM TOIS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "1046-8188" },
    { abbr: "TKDE",   name: "IEEE TKDE",                         tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "IEEE", issn: "1041-4347" },
    { abbr: "VLDBJ",  name: "The VLDB Journal",                  tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "1066-8888" },
    // B
    { abbr: "TKDD",   name: "ACM TKDD",                          tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "1556-4681" },
    { abbr: "TWEB",   name: "ACM Trans. the Web",                tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "1559-1131" },
    { abbr: "AEI",    name: "Advanced Engineering Informatics",  tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "1474-0346" },
    { abbr: "DKE_DB", name: "Data & Knowledge Engineering",      tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0169-023X" },
    { abbr: "DMKD",   name: "Data Mining and Knowledge Discovery", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "1384-5810" },
    { abbr: "EJIS",   name: "European J. Information Systems",   tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "0960-085X" },
    { abbr: "GeoInf", name: "GeoInformatica",                    tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "1384-6175" },
    { abbr: "IPM",    name: "Information Processing & Management", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0306-4573" },
    { abbr: "ISci",   name: "Information Sciences",              tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0020-0255" },
    { abbr: "IS",     name: "Information Systems",               tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0306-4379" },
    { abbr: "JASIST", name: "J. Assoc. Information Science and Technology", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Wiley", issn: "2330-1635" },
    { abbr: "JWS",    name: "Journal of Web Semantics",          tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "1570-8268" },
    { abbr: "KAIS",   name: "Knowledge and Information Systems",  tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "0219-1377" },
    { abbr: "DSE",    name: "Data Science and Engineering",      tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "2364-1185" },
    // C
    { abbr: "DPD",    name: "Distributed and Parallel Databases", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "0926-8782" },
    { abbr: "IandM",  name: "Information & Management",          tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0378-7206" },
    { abbr: "IPL",    name: "Information Processing Letters",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0020-0190" },
    { abbr: "DiscComp", name: "Discover Computing",             tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "2948-2992" },
    { abbr: "IJCIS",  name: "International J. Cooperative Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "World Scientific", issn: "0218-8585" },
    { abbr: "IJGIS",  name: "International J. Geographical Information Science", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Taylor & Francis", issn: "1365-8816" },
    { abbr: "IJIS",   name: "International J. Intelligent Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Wiley", issn: "1098-111X" },
    { abbr: "IJKM",   name: "International J. Knowledge Management", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI", issn: "1546-2234" },
    { abbr: "IJSWIS", name: "International J. Semantic Web and Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI", issn: "1552-6283" },
    { abbr: "JCIS",   name: "Journal of Computer Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IACIS", issn: "0887-4417" },
    { abbr: "JDM",    name: "Journal of Database Management",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "IGI-Global", issn: "1063-8016" },
    { abbr: "JGITM",  name: "Journal of Global Information Technology Management", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Ivy League Publishing", issn: "1097-198X" },
    { abbr: "JIIS",   name: "Journal of Intelligent Information Systems", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Springer", issn: "0925-9902" },
    { abbr: "JSIS",   name: "J. Strategic Information Systems",  tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier", issn: "0963-8687" },
    { abbr: "TIST",   name: "ACM Trans. Intelligent Systems and Technology", tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "2157-6904" },
    { abbr: "TORS",   name: "ACM Trans. Recommender Systems",    tier: "C", domain: "数据库/数据挖掘/内容检索", publisher: "ACM", issn: "2770-6699" },

    // ── 计算机图形学与多媒体 ──────────────────────────────────
    // A
    { abbr: "TOG",    name: "ACM Trans. on Graphics",            tier: "A", domain: "计算机图形学与多媒体", publisher: "ACM", issn: "0730-0301" },
    { abbr: "TIP",    name: "IEEE TIP",                          tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE", issn: "1057-7149" },
    { abbr: "TVCG",   name: "IEEE TVCG",                         tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE", issn: "1077-2626" },
    { abbr: "TMM",    name: "IEEE Trans. Multimedia",            tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE", issn: "1520-9210" },
    // B
    { abbr: "TOMM",   name: "ACM TOMM",                          tier: "B", domain: "计算机图形学与多媒体", publisher: "ACM", issn: "1551-6857" },
    { abbr: "CAGD",   name: "Computer Aided Geometric Design",   tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0167-8396" },
    { abbr: "CGF",    name: "Computer Graphics Forum",           tier: "B", domain: "计算机图形学与多媒体", publisher: "Wiley", issn: "0167-7055" },
    { abbr: "CAD",    name: "Computer-Aided Design",             tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0010-4485" },
    { abbr: "TCSVT",  name: "IEEE TCSVT",                        tier: "B", domain: "计算机图形学与多媒体", publisher: "IEEE", issn: "1051-8215" },
    { abbr: "JASA",   name: "J. the Acoustical Society of America", tier: "B", domain: "计算机图形学与多媒体", publisher: "AIP", issn: "0001-4966" },
    { abbr: "SIIMS",  name: "SIAM J. Imaging Sciences",          tier: "B", domain: "计算机图形学与多媒体", publisher: "SIAM", issn: "1936-4962" },
    { abbr: "SPECOM", name: "Speech Communication",              tier: "B", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0167-6393" },
    { abbr: "CVMJ",   name: "Computational Visual Media",        tier: "B", domain: "计算机图形学与多媒体", publisher: "Springer", issn: "2096-0433" },
    // C
    { abbr: "CGTA",   name: "Computational Geometry: Theory and Applications", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0925-7721" },
    { abbr: "CAVW",   name: "Computer Animation and Virtual Worlds", tier: "C", domain: "计算机图形学与多媒体", publisher: "Wiley", issn: "1546-4261" },
    { abbr: "CandG",  name: "Computers & Graphics",              tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0097-8493" },
    { abbr: "DCG",    name: "Discrete & Computational Geometry",  tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer", issn: "0178-2767" },
    { abbr: "SPL",    name: "IEEE Signal Processing Letters",    tier: "C", domain: "计算机图形学与多媒体", publisher: "IEEE", issn: "1070-9908" },
    { abbr: "IETIPR", name: "IET Image Processing",              tier: "C", domain: "计算机图形学与多媒体", publisher: "IET", issn: "1751-9659" },
    { abbr: "JVCIR",  name: "J. Visual Communication and Image Representation", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "1047-3203" },
    { abbr: "MS",     name: "Multimedia Systems",                tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer", issn: "0942-4962" },
    { abbr: "MTA",    name: "Multimedia Tools and Applications",  tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer", issn: "1380-7501" },
    { abbr: "SIGPRO", name: "Signal Processing",                 tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "2210-6863" },
    { abbr: "SPIC",   name: "Signal Processing: Image Communication", tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "0923-5965" },
    { abbr: "TVC",    name: "The Visual Computer",               tier: "C", domain: "计算机图形学与多媒体", publisher: "Springer", issn: "0178-2789" },
    { abbr: "VI",     name: "Visual Informatics",                tier: "C", domain: "计算机图形学与多媒体", publisher: "浙江大学", issn: "2468-502X" },
    { abbr: "VRIH",   name: "Virtual Reality & Intelligent Hardware", tier: "C", domain: "计算机图形学与多媒体", publisher: "北京航空航天大学", issn: "2096-5764" },
    { abbr: "GMOD",   name: "Graphical Models",                  tier: "C", domain: "计算机图形学与多媒体", publisher: "Elsevier", issn: "1524-0703" },

    // ── 计算机科学理论 ────────────────────────────────────────
    // A
    { abbr: "TIT",    name: "IEEE Trans. Information Theory",    tier: "A", domain: "计算机科学理论", publisher: "IEEE", issn: "0018-9448" },
    { abbr: "IANDC",  name: "Information and Computation",       tier: "A", domain: "计算机科学理论", publisher: "Elsevier", issn: "0890-5401" },
    { abbr: "SICOMP", name: "SIAM J. Computing",                 tier: "A", domain: "计算机科学理论", publisher: "SIAM", issn: "0097-5397" },
    // B
    { abbr: "TALG",   name: "ACM Trans. Algorithms",             tier: "B", domain: "计算机科学理论", publisher: "ACM", issn: "1549-6325" },
    { abbr: "TOCL",   name: "ACM Trans. Computational Logic",    tier: "B", domain: "计算机科学理论", publisher: "ACM", issn: "1529-3785" },
    { abbr: "TOMS",   name: "ACM Trans. Mathematical Software",  tier: "B", domain: "计算机科学理论", publisher: "ACM", issn: "0098-3500" },
    { abbr: "Algor",  name: "Algorithmica",                      tier: "B", domain: "计算机科学理论", publisher: "Springer", issn: "0178-4617" },
    { abbr: "CC",     name: "Computational Complexity",          tier: "B", domain: "计算机科学理论", publisher: "Springer", issn: "1016-3328" },
    { abbr: "FAC",    name: "Formal Aspects of Computing",       tier: "B", domain: "计算机科学理论", publisher: "Springer", issn: "0934-5043" },
    { abbr: "FMSD",   name: "Formal Methods in System Design",   tier: "B", domain: "计算机科学理论", publisher: "Springer", issn: "0925-9856" },
    { abbr: "INFORMS", name: "INFORMS J. Computing",            tier: "B", domain: "计算机科学理论", publisher: "INFORMS", issn: "1091-9856" },
    { abbr: "JCSS",   name: "J. Computer and System Sciences",   tier: "B", domain: "计算机科学理论", publisher: "Elsevier", issn: "0022-0000" },
    { abbr: "JGO",    name: "J. Global Optimization",            tier: "B", domain: "计算机科学理论", publisher: "Springer", issn: "0925-5001" },
    { abbr: "JSC",    name: "J. Symbolic Computation",           tier: "B", domain: "计算机科学理论", publisher: "Elsevier", issn: "0747-7171" },
    { abbr: "MSCS",   name: "Mathematical Structures in Computer Science", tier: "B", domain: "计算机科学理论", publisher: "Cambridge", issn: "0960-1295" },
    { abbr: "TCS",    name: "Theoretical Computer Science",      tier: "B", domain: "计算机科学理论", publisher: "Elsevier", issn: "0304-3975" },
    // C
    { abbr: "ACTA",   name: "Acta Informatica",                  tier: "C", domain: "计算机科学理论", publisher: "Springer", issn: "0001-5903" },
    { abbr: "APAL",   name: "Annals of Pure and Applied Logic",   tier: "C", domain: "计算机科学理论", publisher: "Elsevier", issn: "0168-0072" },
    { abbr: "DAM",    name: "Discrete Applied Mathematics",      tier: "C", domain: "计算机科学理论", publisher: "Elsevier", issn: "0166-218X" },
    { abbr: "FUIN",   name: "Fundamenta Informaticae",           tier: "C", domain: "计算机科学理论", publisher: "IOS Press", issn: "0169-2968" },
    { abbr: "IPL_T",  name: "Information Processing Letters (Theory)", tier: "C", domain: "计算机科学理论", publisher: "Elsevier", issn: "0020-0190" },
    { abbr: "JCOMPL", name: "Journal of Complexity",             tier: "C", domain: "计算机科学理论", publisher: "Elsevier", issn: "0885-064X" },
    { abbr: "LOGCOM", name: "J. Logic and Computation",          tier: "C", domain: "计算机科学理论", publisher: "Oxford", issn: "0955-792X" },
    { abbr: "JSL",    name: "J. Symbolic Logic",                 tier: "C", domain: "计算机科学理论", publisher: "ASL", issn: "0022-4812" },
    { abbr: "LMCS",   name: "Logical Methods in Computer Science", tier: "C", domain: "计算机科学理论", publisher: "LMCS", issn: "1860-5974" },
    { abbr: "SIDMA",  name: "SIAM J. Discrete Mathematics",      tier: "C", domain: "计算机科学理论", publisher: "SIAM", issn: "0895-4801" },
    { abbr: "ToCS",   name: "Theory of Computing Systems",       tier: "C", domain: "计算机科学理论", publisher: "Springer", issn: "1432-4350" },
    { abbr: "TQC",    name: "ACM Trans. Quantum Computing",      tier: "C", domain: "计算机科学理论", publisher: "ACM", issn: "2643-6809" },

    // ── 软件工程/系统软件/程序设计语言 ────────────────────────
    // A
    { abbr: "TOPLAS", name: "ACM TOPLAS",                        tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM", issn: "0164-0925" },
    { abbr: "TOSEM",  name: "ACM TOSEM",                         tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM", issn: "1049-331X" },
    { abbr: "TSE",    name: "IEEE TSE",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE", issn: "0098-5589" },
    { abbr: "TSC",    name: "IEEE TSC",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE", issn: "1939-1374" },
    // B
    { abbr: "ASE_J",  name: "Automated Software Engineering",    tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "0928-8910" },
    { abbr: "ESE",    name: "Empirical Software Engineering",    tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "1382-3256" },
    { abbr: "IETS",   name: "IET Software",                      tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "IET", issn: "1751-8806" },
    { abbr: "IST",    name: "Information and Software Technology", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier", issn: "0950-5849" },
    { abbr: "JFP",    name: "Journal of Functional Programming",  tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Cambridge", issn: "0956-7968" },
    { abbr: "JSEP",   name: "Journal of Software: Evolution and Process", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley", issn: "2047-7473" },
    { abbr: "JSS",    name: "J. Systems and Software",           tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier", issn: "0164-1212" },
    { abbr: "RE",     name: "Requirements Engineering",          tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "0947-3602" },
    { abbr: "SCP",    name: "Science of Computer Programming",   tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier", issn: "0167-6423" },
    { abbr: "SoSyM",  name: "Software and Systems Modeling",     tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "1619-1366" },
    { abbr: "STVR",   name: "Software Testing, Verification and Reliability", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley", issn: "0960-0833" },
    { abbr: "SPE",    name: "Software: Practice and Experience",  tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Wiley", issn: "0038-0644" },
    // C
    { abbr: "CL_J",   name: "Computer Languages, Systems & Structures", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier", issn: "1477-8357" },
    { abbr: "IJSEKE", name: "International J. Software Engineering and Knowledge Engineering", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "World Scientific", issn: "0218-1940" },
    { abbr: "STTT",   name: "International J. Software Tools for Technology Transfer", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "1613-4207" },
    { abbr: "JLAMP",  name: "J. Logical and Algebraic Methods in Programming", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier", issn: "2352-2208" },
    { abbr: "JWE",    name: "Journal of Web Engineering",        tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Rinton Press", issn: "1540-9589" },
    { abbr: "SOCA",   name: "Service Oriented Computing and Applications", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "1863-2386" },
    { abbr: "SQJ",    name: "Software Quality Journal",          tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer", issn: "0963-9314" },
    { abbr: "TPLP",   name: "Theory and Practice of Logic Programming", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "Cambridge", issn: "1471-0684" },
    { abbr: "PACMPL", name: "Proceedings of the ACM on Programming Languages", tier: "C", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM", issn: "2475-1421" },

    // ── 计算机网络 ────────────────────────────────────────────
    // A
    { abbr: "JSAC",   name: "IEEE J. Selected Areas in Communications", tier: "A", domain: "计算机网络", publisher: "IEEE", issn: "0733-8716" },
    { abbr: "TMC",    name: "IEEE Trans. Mobile Computing",      tier: "A", domain: "计算机网络", publisher: "IEEE", issn: "1536-1233" },
    { abbr: "TON",    name: "IEEE/ACM Trans. Networking",        tier: "A", domain: "计算机网络", publisher: "IEEE", issn: "1063-6692" },
    // B
    { abbr: "TOIT",   name: "ACM Trans. Internet Technology",    tier: "B", domain: "计算机网络", publisher: "ACM", issn: "1533-5399" },
    { abbr: "TOSN",   name: "ACM Trans. Sensor Networks",        tier: "B", domain: "计算机网络", publisher: "ACM", issn: "1550-4859" },
    { abbr: "CN",     name: "Computer Networks",                 tier: "B", domain: "计算机网络", publisher: "Elsevier", issn: "1389-1286" },
    { abbr: "TCOMM",  name: "IEEE Trans. Communications",        tier: "B", domain: "计算机网络", publisher: "IEEE", issn: "0090-6778" },
    { abbr: "TWC",    name: "IEEE Trans. Wireless Communications", tier: "B", domain: "计算机网络", publisher: "IEEE", issn: "1536-1276" },
    // C
    { abbr: "AdHoc",  name: "Ad Hoc Networks",                   tier: "C", domain: "计算机网络", publisher: "Elsevier", issn: "1570-8705" },
    { abbr: "ComCom", name: "Computer Communications",           tier: "C", domain: "计算机网络", publisher: "Elsevier", issn: "0140-3664" },
    { abbr: "TNSM",   name: "IEEE Trans. Network and Service Management", tier: "C", domain: "计算机网络", publisher: "IEEE", issn: "1932-4537" },
    { abbr: "IETComm", name: "IET Communications",              tier: "C", domain: "计算机网络", publisher: "IET", issn: "1751-8628" },
    { abbr: "JNCA",   name: "J. Network and Computer Applications", tier: "C", domain: "计算机网络", publisher: "Elsevier", issn: "1084-8045" },
    { abbr: "MONET",  name: "Mobile Networks and Applications",   tier: "C", domain: "计算机网络", publisher: "Springer", issn: "1383-469X" },
    { abbr: "Networks", name: "Networks",                        tier: "C", domain: "计算机网络", publisher: "Wiley", issn: "0028-3045" },
    { abbr: "PPNA",   name: "Peer-to-Peer Networking and Applications", tier: "C", domain: "计算机网络", publisher: "Springer", issn: "1936-6442" },
    { abbr: "WCMC",   name: "Wireless Communications and Mobile Computing", tier: "C", domain: "计算机网络", publisher: "Wiley", issn: "1530-8669" },
    { abbr: "WiNet",  name: "Wireless Networks",                 tier: "C", domain: "计算机网络", publisher: "Springer", issn: "1022-0038" },
    { abbr: "IOT",    name: "IEEE Internet of Things Journal",   tier: "C", domain: "计算机网络", publisher: "IEEE", issn: "2327-4662" },
    { abbr: "TIOT",   name: "ACM Trans. Internet of Things",     tier: "C", domain: "计算机网络", publisher: "ACM", issn: "2577-6207" },

    // ── 网络与信息安全 ────────────────────────────────────────
    // A
    { abbr: "TDSC",   name: "IEEE TDSC",                         tier: "A", domain: "网络与信息安全", publisher: "IEEE", issn: "1545-5971" },
    { abbr: "TIFS",   name: "IEEE TIFS",                         tier: "A", domain: "网络与信息安全", publisher: "IEEE", issn: "1556-6013" },
    { abbr: "JOC",    name: "Journal of Cryptology",             tier: "A", domain: "网络与信息安全", publisher: "Springer", issn: "0933-2790" },
    // B
    { abbr: "TOPS",   name: "ACM Trans. Privacy and Security",   tier: "B", domain: "网络与信息安全", publisher: "ACM", issn: "2471-2566" },
    { abbr: "CompSec", name: "Computers & Security",             tier: "B", domain: "网络与信息安全", publisher: "Elsevier", issn: "0167-4048" },
    { abbr: "DCC",    name: "Designs, Codes and Cryptography",   tier: "B", domain: "网络与信息安全", publisher: "Springer", issn: "0925-1022" },
    { abbr: "JCS",    name: "J. Computer Security",              tier: "B", domain: "网络与信息安全", publisher: "IOS Press", issn: "0926-227X" },
    { abbr: "Cybersec", name: "Cybersecurity",                   tier: "B", domain: "网络与信息安全", publisher: "Springer", issn: "2523-3246" },
    // C
    { abbr: "CLSR",   name: "Computer Law & Security Review",    tier: "C", domain: "网络与信息安全", publisher: "Elsevier", issn: "0267-3649" },
    { abbr: "EJISec", name: "EURASIP J. Information Security",   tier: "C", domain: "网络与信息安全", publisher: "Springer", issn: "1687-4161" },
    { abbr: "IETIFS", name: "IET Information Security",           tier: "C", domain: "网络与信息安全", publisher: "IET", issn: "1751-8709" },
    { abbr: "IMCS",   name: "Information and Computer Security",  tier: "C", domain: "网络与信息安全", publisher: "Emerald", issn: "2056-4961" },
    { abbr: "IJICS",  name: "International J. Information and Computer Security", tier: "C", domain: "网络与信息安全", publisher: "Inderscience", issn: "1752-0890" },
    { abbr: "IJISP",  name: "International J. Information Security and Privacy", tier: "C", domain: "网络与信息安全", publisher: "IGI Global", issn: "1934-2111" },
    { abbr: "JISA",   name: "J. Information Security and Applications", tier: "C", domain: "网络与信息安全", publisher: "Elsevier", issn: "2214-2126" },
    { abbr: "SCN",    name: "Security and Communication Networks", tier: "C", domain: "网络与信息安全", publisher: "Wiley", issn: "1939-0114" },
    { abbr: "HCC",    name: "High-Confidence Computing",         tier: "C", domain: "网络与信息安全", publisher: "Elsevier", issn: "2667-2952" },

    // ── 计算机体系结构/并行与分布计算/存储系统 ────────────────
    // A
    { abbr: "TOCS",   name: "ACM Trans. Computer Systems",       tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "0734-2071" },
    { abbr: "TOS",    name: "ACM Trans. Storage",                tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1553-3077" },
    { abbr: "TCAD",   name: "IEEE TCAD",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "0278-0070" },
    { abbr: "TC",     name: "IEEE Trans. Computers",             tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "0018-9340" },
    { abbr: "TPDS",   name: "IEEE TPDS",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "1045-9219" },
    { abbr: "TACO",   name: "ACM Trans. Architecture and Code Optimization", tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1544-3566" },
    // B
    { abbr: "TAAS",   name: "ACM Trans. Autonomous and Adaptive Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1556-4665" },
    { abbr: "TODAES", name: "ACM Trans. Design Automation of Electronic Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1084-4309" },
    { abbr: "TECS",   name: "ACM Trans. Embedded Computing Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1539-9087" },
    { abbr: "TRETS",  name: "ACM Trans. Reconfigurable Technology and Systems", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1936-7406" },
    { abbr: "TVLSI",  name: "IEEE Trans. VLSI Systems",          tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "1063-8210" },
    { abbr: "JPDC",   name: "J. Parallel and Distributed Computing", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "0743-7315" },
    { abbr: "JSA",    name: "J. Systems Architecture",           tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "1383-7621" },
    { abbr: "ParComp", name: "Parallel Computing",              tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "0167-8191" },
    { abbr: "PEval",  name: "Performance Evaluation",            tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "0166-5316" },
    { abbr: "TCC",    name: "IEEE Trans. Cloud Computing",       tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "2168-7161" },
    // C
    { abbr: "JETC",   name: "ACM J. Emerging Technologies in Computing Systems", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "ACM", issn: "1550-4832" },
    { abbr: "Concurr", name: "Concurrency and Computation: Practice and Experience", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Wiley", issn: "1532-0626" },
    { abbr: "DC",     name: "Distributed Computing",             tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer", issn: "0178-2770" },
    { abbr: "FGCS",   name: "Future Generation Computer Systems", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "0167-739X" },
    { abbr: "Integr",  name: "Integration, the VLSI Journal",   tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier", issn: "0167-9260" },
    { abbr: "JETTA",  name: "J. Electronic Testing",             tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer", issn: "0923-8174" },
    { abbr: "JGC",    name: "Journal of Grid Computing",         tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer", issn: "1570-7873" },
    { abbr: "RTS",    name: "Real-Time Systems",                 tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer", issn: "0922-6443" },
    { abbr: "TJSC",   name: "The Journal of Supercomputing",     tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Springer", issn: "0920-8542" },
    { abbr: "TCASI",  name: "IEEE Trans. Circuits and Systems I", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "1549-8328" },
    { abbr: "THPC",   name: "CCF Trans. High Performance Computing", tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "CCF", issn: "2524-4922" },
    { abbr: "TSUSC",  name: "IEEE Trans. Sustainable Computing",  tier: "C", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE", issn: "2377-3782" },

    // ── 人机交互与普适计算 ────────────────────────────────────
    // A
    { abbr: "TOCHI",  name: "ACM TOCHI",                         tier: "A", domain: "人机交互与普适计算", publisher: "ACM", issn: "1073-0516" },
    { abbr: "IJHCS",  name: "Int. J. Human-Computer Studies",    tier: "A", domain: "人机交互与普适计算", publisher: "Elsevier", issn: "1071-5819" },
    // B
    { abbr: "CSCW_J", name: "Computer Supported Cooperative Work", tier: "B", domain: "人机交互与普适计算", publisher: "Springer", issn: "0925-9724" },
    { abbr: "HCI",    name: "Human-Computer Interaction",        tier: "B", domain: "人机交互与普适计算", publisher: "Taylor & Francis", issn: "0737-0024" },
    { abbr: "THMS",   name: "IEEE Trans. Human-Machine Systems", tier: "B", domain: "人机交互与普适计算", publisher: "IEEE", issn: "2168-2291" },
    { abbr: "IWC",    name: "Interacting with Computers",        tier: "B", domain: "人机交互与普适计算", publisher: "Oxford", issn: "0953-5438" },
    { abbr: "IJHCI",  name: "International J. Human-Computer Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Taylor & Francis", issn: "1044-7318" },
    { abbr: "UMUAI",  name: "User Modeling and User-Adapted Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Springer", issn: "0924-1868" },
    { abbr: "TSMC",   name: "IEEE Trans. Systems, Man, and Cybernetics: Systems", tier: "B", domain: "人机交互与普适计算", publisher: "IEEE", issn: "2168-2216" },
    { abbr: "TPCI",   name: "CCF Trans. Pervasive Computing and Interaction", tier: "B", domain: "人机交互与普适计算", publisher: "Springer", issn: "2524-521X" },
    // C
    { abbr: "BIT",    name: "Behaviour & Information Technology", tier: "C", domain: "人机交互与普适计算", publisher: "Taylor & Francis", issn: "0144-929X" },
    { abbr: "PUC",    name: "Personal and Ubiquitous Computing",  tier: "C", domain: "人机交互与普适计算", publisher: "Springer", issn: "1617-4909" },
    { abbr: "PMC",    name: "Pervasive and Mobile Computing",    tier: "C", domain: "人机交互与普适计算", publisher: "Elsevier", issn: "1574-1192" },
    { abbr: "PACMHCI", name: "Proceedings of the ACM on Human-Computer Interaction", tier: "C", domain: "人机交互与普适计算", publisher: "ACM", issn: "2573-0142" },
    { abbr: "THRI",   name: "ACM Trans. Human-Robot Interaction", tier: "C", domain: "人机交互与普适计算", publisher: "ACM", issn: "2573-9522" },

    // ── 交叉/综合/新兴 ────────────────────────────────────────
    // A
    { abbr: "JACM",   name: "Journal of the ACM",                tier: "A", domain: "交叉/综合/新兴", publisher: "ACM", issn: "0004-5411" },
    { abbr: "ProcIEEE", name: "Proceedings of the IEEE",         tier: "A", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "0018-9219" },
    { abbr: "SCIS",   name: "Science China Information Sciences", tier: "A", domain: "交叉/综合/新兴", publisher: "Springer", issn: "1674-733X" },
    { abbr: "Bioinf", name: "Bioinformatics",                    tier: "A", domain: "交叉/综合/新兴", publisher: "Oxford", issn: "1367-4803" },
    // B
    { abbr: "BriefBio", name: "Briefings in Bioinformatics",    tier: "B", domain: "交叉/综合/新兴", publisher: "Oxford", issn: "1467-5463" },
    { abbr: "Cognition", name: "Cognition",                     tier: "B", domain: "交叉/综合/新兴", publisher: "Elsevier", issn: "2595-8801" },
    { abbr: "TASE",   name: "IEEE Trans. Automation Science and Engineering", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "1545-5955" },
    { abbr: "TGRS",   name: "IEEE Trans. Geoscience and Remote Sensing", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "0196-2892" },
    { abbr: "TITS",   name: "IEEE Trans. Intelligent Transportation Systems", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "1524-9050" },
    { abbr: "TMI",    name: "IEEE Trans. Medical Imaging",       tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "0278-0062" },
    { abbr: "TR",     name: "IEEE Trans. Robotics",              tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "1552-3098" },
    { abbr: "TCBB",   name: "IEEE/ACM TCBB",                     tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE/ACM", issn: "2373-7725" },
    { abbr: "JCST",   name: "J. Computer Science and Technology", tier: "B", domain: "交叉/综合/新兴", publisher: "Springer", issn: "1000-9000" },
    { abbr: "JAMIA",  name: "J. American Medical Informatics Association", tier: "B", domain: "交叉/综合/新兴", publisher: "BMJ", issn: "1527-974X" },
    { abbr: "PLOSCB", name: "PLOS Computational Biology",       tier: "B", domain: "交叉/综合/新兴", publisher: "PLOS", issn: "1553-734X" },
    { abbr: "CompJ",  name: "The Computer Journal",              tier: "B", domain: "交叉/综合/新兴", publisher: "Oxford", issn: "1073-0486" },
    { abbr: "WWW_J",  name: "World Wide Web",                   tier: "B", domain: "交叉/综合/新兴", publisher: "Springer", issn: "1386-145X" },
    { abbr: "FCS",    name: "Frontiers of Computer Science",     tier: "B", domain: "交叉/综合/新兴", publisher: "Springer", issn: "2095-2228" },
    { abbr: "BCRA",   name: "Blockchain: Research and Applications", tier: "B", domain: "交叉/综合/新兴", publisher: "Elsevier", issn: "2096-7209" },
    // C
    { abbr: "BMCBio", name: "BMC Bioinformatics",                tier: "C", domain: "交叉/综合/新兴", publisher: "BioMed Central", issn: "1471-2105" },
    { abbr: "CybSys", name: "Cybernetics and Systems",           tier: "C", domain: "交叉/综合/新兴", publisher: "Taylor & Francis", issn: "1060-0396" },
    { abbr: "GRSL",   name: "IEEE Geoscience and Remote Sensing Letters", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "1545-598X" },
    { abbr: "JBHI",   name: "IEEE J. Biomedical and Health Informatics", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "2168-2194" },
    { abbr: "TBD",    name: "IEEE Trans. Big Data",              tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "2332-7790" },
    { abbr: "IETITS", name: "IET Intelligent Transport Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "IET", issn: "1751-956X" },
    { abbr: "JBI",    name: "J. Biomedical Informatics",         tier: "C", domain: "交叉/综合/新兴", publisher: "Elsevier", issn: "1532-0464" },
    { abbr: "MedIA",  name: "Medical Image Analysis",            tier: "C", domain: "交叉/综合/新兴", publisher: "Elsevier", issn: "1361-8415" },
    { abbr: "TII",    name: "IEEE Trans. Industrial Informatics", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "1551-3203" },
    { abbr: "TCPS",   name: "ACM Trans. Cyber-Physical Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM", issn: "2378-962X" },
    { abbr: "TOCE",   name: "ACM Trans. Computing Education",    tier: "C", domain: "交叉/综合/新兴", publisher: "ACM", issn: "1946-6226" },
    { abbr: "EITEE",  name: "Engineering IT & Electronic Engineering", tier: "C", domain: "交叉/综合/新兴", publisher: "浙江大学", issn: "2096-5764" },
    { abbr: "TCSS",   name: "IEEE Trans. Computational Social Systems", tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "2329-924X" },
    { abbr: "TRel",   name: "IEEE Trans. Reliability",           tier: "C", domain: "交叉/综合/新兴", publisher: "IEEE", issn: "0018-9529" },
    { abbr: "HEALTH", name: "ACM Trans. Computing for Healthcare", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM", issn: "2637-8051" },
    { abbr: "ACMDLT", name: "ACM Distributed Ledger Technologies", tier: "C", domain: "交叉/综合/新兴", publisher: "ACM", issn: "2576-8348" },
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
