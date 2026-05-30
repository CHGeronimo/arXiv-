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
    { venue: "IJCAI",  tier: "B", domain: "人工智能" },
    { venue: "EMNLP",  tier: "B", domain: "人工智能" },
    { venue: "ECCV",   tier: "B", domain: "人工智能" },
    { venue: "NAACL",  tier: "B", domain: "人工智能" },
    { venue: "COLING", tier: "B", domain: "人工智能" },
    { venue: "ICRA",   tier: "B", domain: "人工智能" },
    { venue: "UAI",    tier: "B", domain: "人工智能" },
    { venue: "AAMAS",  tier: "B", domain: "人工智能" },
    { venue: "ECAI",   tier: "B", domain: "人工智能" },
    { venue: "KR",     tier: "B", domain: "人工智能" },
    { venue: "COLT",   tier: "B", domain: "人工智能" },
    { venue: "ICAPS",  tier: "B", domain: "人工智能" },
    // C
    { venue: "AISTATS", tier: "C", domain: "人工智能" },
    { venue: "BMVC",    tier: "C", domain: "人工智能" },
    { venue: "MICCAI",  tier: "C", domain: "人工智能" },
    { venue: "IROS",    tier: "C", domain: "人工智能" },
    { venue: "FG",      tier: "C", domain: "人工智能" },
    { venue: "ICPR",    tier: "C", domain: "人工智能" },
    { venue: "ICDAR",   tier: "C", domain: "人工智能" },
    { venue: "ICANN",   tier: "C", domain: "人工智能" },
    { venue: "ICONIP",  tier: "C", domain: "人工智能" },
    { venue: "NLPCC",   tier: "C", domain: "人工智能" },
    { venue: "ACCV",    tier: "C", domain: "人工智能" },
    { venue: "ACML",    tier: "C", domain: "人工智能" },
    { venue: "GECCO",   tier: "C", domain: "人工智能" },

    // ── 数据库/数据挖掘/内容检索 ──────────────────────────────
    // A
    { venue: "SIGMOD", tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SIGKDD", tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ICDE",   tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SIGIR",  tier: "A", domain: "数据库/数据挖掘/内容检索" },
    { venue: "VLDB",   tier: "A", domain: "数据库/数据挖掘/内容检索" },
    // B
    { venue: "WWW",    tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "WSDM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "CIKM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ICDM",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "RecSys", tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "SDM",    tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ECML-PKDD", tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "EDBT",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    { venue: "PODS",   tier: "B", domain: "数据库/数据挖掘/内容检索" },
    // C
    { venue: "PAKDD",  tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "ECIR",   tier: "C", domain: "数据库/数据挖掘/内容检索" },
    { venue: "DASFAA", tier: "C", domain: "数据库/数据挖掘/内容检索" },

    // ── 计算机图形学与多媒体 ──────────────────────────────────
    // A
    { venue: "ACMMM",    tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "SIGGRAPH", tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "IEEEVIS",  tier: "A", domain: "计算机图形学与多媒体" },
    { venue: "VR",       tier: "A", domain: "计算机图形学与多媒体" },
    // B
    { venue: "ICASSP",      tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "INTERSPEECH", tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ICME",        tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ISMAR",       tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "Eurographics", tier: "B", domain: "计算机图形学与多媒体" },
    { venue: "ICMR",        tier: "B", domain: "计算机图形学与多媒体" },
    // C
    { venue: "3DV",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "ICIP",   tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "PG",     tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "CVM",    tier: "C", domain: "计算机图形学与多媒体" },
    { venue: "PRCV",   tier: "C", domain: "计算机图形学与多媒体" },

    // ── 计算机科学理论 ────────────────────────────────────────
    // A
    { venue: "STOC", tier: "A", domain: "计算机科学理论" },
    { venue: "FOCS", tier: "A", domain: "计算机科学理论" },
    { venue: "SODA", tier: "A", domain: "计算机科学理论" },
    { venue: "LICS", tier: "A", domain: "计算机科学理论" },
    { venue: "CAV",  tier: "A", domain: "计算机科学理论" },
    // B
    { venue: "ICALP", tier: "B", domain: "计算机科学理论" },
    { venue: "ESA",   tier: "B", domain: "计算机科学理论" },
    { venue: "ICALP", tier: "B", domain: "计算机科学理论" },

    // ── 软件工程/系统软件/程序设计语言 ────────────────────────
    // A
    { venue: "ICSE",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "FSE",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "SOSP",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "OSDI",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "PLDI",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "POPL",  tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "OOPSLA", tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ASE",   tier: "A", domain: "软件工程/系统软件/程序设计语言" },
    // B
    { venue: "ISSTA",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICFP",   tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ECOOP",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "MSR",    tier: "B", domain: "软件工程/系统软件/程序设计语言" },
    { venue: "ICSME",  tier: "B", domain: "软件工程/系统软件/程序设计语言" },

    // ── 计算机网络 ────────────────────────────────────────────
    // A
    { venue: "SIGCOMM", tier: "A", domain: "计算机网络" },
    { venue: "NSDI",    tier: "A", domain: "计算机网络" },
    // B
    { venue: "INFOCOM", tier: "B", domain: "计算机网络" },
    { venue: "CoNEXT",  tier: "B", domain: "计算机网络" },
    { venue: "IMC",     tier: "B", domain: "计算机网络" },

    // ── 网络与信息安全 ────────────────────────────────────────
    // A
    { venue: "S&P",          tier: "A", domain: "网络与信息安全" },
    { venue: "CCS",          tier: "A", domain: "网络与信息安全" },
    { venue: "USENIXSecurity", tier: "A", domain: "网络与信息安全" },
    { venue: "NDSS",         tier: "A", domain: "网络与信息安全" },
    // B
    { venue: "EuroS&P",     tier: "B", domain: "网络与信息安全" },
    { venue: "AsiaCCS",     tier: "B", domain: "网络与信息安全" },
    { venue: "ACSAC",       tier: "B", domain: "网络与信息安全" },

    // ── 计算机体系结构/并行与分布计算/存储系统 ────────────────
    // A
    { venue: "ISCA",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "MICRO",  tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "HPCA",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ASPLOS", tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "SC",     tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "DAC",    tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "FAST",   tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统" },
    // B
    { venue: "DATE",    tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "SoCC",    tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "ICDCS",   tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "IPDPS",   tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "EuroSys", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "HPDC",    tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },
    { venue: "PACT",    tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统" },

    // ── 人机交互与普适计算 ────────────────────────────────────
    // A
    { venue: "CHI",   tier: "A", domain: "人机交互与普适计算" },
    { venue: "CSCW",  tier: "A", domain: "人机交互与普适计算" },
    { venue: "UbiComp", tier: "A", domain: "人机交互与普适计算" },
    { venue: "UIST",  tier: "A", domain: "人机交互与普适计算" },
    // B
    { venue: "IUI",      tier: "B", domain: "人机交互与普适计算" },
    { venue: "MobileHCI", tier: "B", domain: "人机交互与普适计算" },
    { venue: "PERCOM",   tier: "B", domain: "人机交互与普适计算" },

    // ── 交叉/综合/新兴 ────────────────────────────────────────
    // A
    { venue: "RTSS", tier: "A", domain: "交叉/综合/新兴" },
    // B
    { venue: "MICCAI_conf", tier: "B", domain: "交叉/综合/新兴" },
    { venue: "RECOMB", tier: "B", domain: "交叉/综合/新兴" },
    // C
    { venue: "IEEEBigData", tier: "C", domain: "交叉/综合/新兴" },
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
    { abbr: "TNNLS",  name: "IEEE TNNLS",                        tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "JAIR",   name: "Journal of Artificial Intelligence Research", tier: "B", domain: "人工智能", publisher: "AAAI" },
    { abbr: "PR",     name: "Pattern Recognition",               tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "CVIU",   name: "Computer Vision and Image Understanding", tier: "B", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "TACL",   name: "Transactions of the ACL",           tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "TASLP",  name: "IEEE TASLP",                        tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TEC",    name: "IEEE Trans. Evolutionary Computation", tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "TFS",    name: "IEEE Trans. Fuzzy Systems",         tier: "B", domain: "人工智能", publisher: "IEEE" },
    { abbr: "ML",     name: "Machine Learning",                  tier: "B", domain: "人工智能", publisher: "Springer" },
    { abbr: "NeurComp", name: "Neural Computation",              tier: "B", domain: "人工智能", publisher: "MIT Press" },
    { abbr: "NN",     name: "Neural Networks",                   tier: "B", domain: "人工智能", publisher: "Elsevier" },
    // C
    { abbr: "ESWA",   name: "Expert Systems with Applications",  tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "KBS",    name: "Knowledge-Based Systems",           tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "Neurocomp", name: "Neurocomputing",                 tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "PRL",    name: "Pattern Recognition Letters",       tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "EAAI",   name: "Engineering Applications of AI",    tier: "C", domain: "人工智能", publisher: "Elsevier" },
    { abbr: "CSL",    name: "Computer Speech & Language",        tier: "C", domain: "人工智能", publisher: "Elsevier" },

    // ── 数据库/数据挖掘/内容检索 ──────────────────────────────
    // A
    { abbr: "TODS",   name: "ACM TODS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TOIS",   name: "ACM TOIS",                          tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "TKDE",   name: "IEEE TKDE",                         tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "IEEE" },
    { abbr: "VLDBJ",  name: "The VLDB Journal",                  tier: "A", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    // B
    { abbr: "DMKD",   name: "Data Mining and Knowledge Discovery", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },
    { abbr: "IPM",    name: "Information Processing & Management", tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "ISci",   name: "Information Sciences",              tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Elsevier" },
    { abbr: "TKDD",   name: "ACM TKDD",                          tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "ACM" },
    { abbr: "KAIS",   name: "Knowledge and Information Systems",  tier: "B", domain: "数据库/数据挖掘/内容检索", publisher: "Springer" },

    // ── 计算机图形学与多媒体 ──────────────────────────────────
    // A
    { abbr: "TOG",    name: "ACM Trans. on Graphics",            tier: "A", domain: "计算机图形学与多媒体", publisher: "ACM" },
    { abbr: "TIP",    name: "IEEE TIP",                          tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "TVCG",   name: "IEEE TVCG",                         tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "TMM",    name: "IEEE Trans. Multimedia",            tier: "A", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    // B
    { abbr: "TCSVT",  name: "IEEE TCSVT",                        tier: "B", domain: "计算机图形学与多媒体", publisher: "IEEE" },
    { abbr: "TOMM",   name: "ACm TOMM",                          tier: "B", domain: "计算机图形学与多媒体", publisher: "ACM" },
    { abbr: "CGF",    name: "Computer Graphics Forum",           tier: "B", domain: "计算机图形学与多媒体", publisher: "Wiley" },

    // ── 计算机科学理论 ────────────────────────────────────────
    // A
    { abbr: "TIT",    name: "IEEE Trans. Information Theory",    tier: "A", domain: "计算机科学理论", publisher: "IEEE" },
    { abbr: "SICOMP", name: "SIAM J. Computing",                 tier: "A", domain: "计算机科学理论", publisher: "SIAM" },
    { abbr: "IANDC",  name: "Information and Computation",       tier: "A", domain: "计算机科学理论", publisher: "Elsevier" },
    // B
    { abbr: "TALG",   name: "ACm TALG",                          tier: "B", domain: "计算机科学理论", publisher: "ACM" },
    { abbr: "JCSS",   name: "J. Computer and System Sciences",   tier: "B", domain: "计算机科学理论", publisher: "Elsevier" },
    { abbr: "TCS",    name: "Theoretical Computer Science",      tier: "B", domain: "计算机科学理论", publisher: "Elsevier" },

    // ── 软件工程/系统软件/程序设计语言 ────────────────────────
    // A
    { abbr: "TOPLAS", name: "ACM TOPLAS",                        tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM" },
    { abbr: "TOSEM",  name: "ACM TOSEM",                         tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "ACM" },
    { abbr: "TSE",    name: "IEEE TSE",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE" },
    { abbr: "TSC",    name: "IEEE TSC",                          tier: "A", domain: "软件工程/系统软件/程序设计语言", publisher: "IEEE" },
    // B
    { abbr: "ASE",    name: "Automated Software Engineering",    tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Springer" },
    { abbr: "IST",    name: "Information and Software Technology", tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },
    { abbr: "JSS",    name: "J. Systems and Software",           tier: "B", domain: "软件工程/系统软件/程序设计语言", publisher: "Elsevier" },

    // ── 计算机网络 ────────────────────────────────────────────
    // A
    { abbr: "TON",    name: "IEEE/ACM Trans. Networking",        tier: "A", domain: "计算机网络", publisher: "IEEE" },
    // B
    { abbr: "TMC",    name: "IEEE Trans. Mobile Computing",      tier: "B", domain: "计算机网络", publisher: "IEEE" },
    { abbr: "TCOMM",  name: "IEEE Trans. Communications",        tier: "B", domain: "计算机网络", publisher: "IEEE" },

    // ── 网络与信息安全 ────────────────────────────────────────
    // A
    { abbr: "TDSC",   name: "IEEE TDSC",                         tier: "A", domain: "网络与信息安全", publisher: "IEEE" },
    // B
    { abbr: "TIFS",   name: "IEEE TIFS",                         tier: "B", domain: "网络与信息安全", publisher: "IEEE" },
    { abbr: "JCS",    name: "J. Computer Security",              tier: "B", domain: "网络与信息安全", publisher: "IOS Press" },

    // ── 计算机体系结构/并行与分布计算/存储系统 ────────────────
    // A
    { abbr: "TC",     name: "IEEE Trans. Computers",             tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "TPDS",   name: "IEEE TPDS",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "TCAD",   name: "IEEE TCAD",                         tier: "A", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    // B
    { abbr: "TCC",    name: "IEEE Trans. Cloud Computing",       tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "IEEE" },
    { abbr: "JPDC",   name: "J. Parallel and Distributed Computing", tier: "B", domain: "计算机体系结构/并行与分布计算/存储系统", publisher: "Elsevier" },

    // ── 人机交互与普适计算 ────────────────────────────────────
    // A
    { abbr: "TOCHI",  name: "ACM TOCHI",                         tier: "A", domain: "人机交互与普适计算", publisher: "ACM" },
    { abbr: "IJHCS",  name: "Int. J. Human-Computer Studies",    tier: "A", domain: "人机交互与普适计算", publisher: "Elsevier" },

    // ── 交叉/综合/新兴 ────────────────────────────────────────
    // A
    { abbr: "JACM",   name: "Journal of the ACM",                tier: "A", domain: "交叉/综合/新兴", publisher: "ACM" },
    { abbr: "ProcIEEE", name: "Proceedings of the IEEE",         tier: "A", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "Bioinf", name: "Bioinformatics",                    tier: "A", domain: "交叉/综合/新兴", publisher: "Oxford" },
    // B
    { abbr: "TMI",    name: "IEEE Trans. Medical Imaging",       tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TR",     name: "IEEE Trans. Robotics",              tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
    { abbr: "TCBB",   name: "IEEE/ACM TCBB",                     tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE/ACM" },
    { abbr: "TITS",   name: "IEEE Trans. Intelligent Transportation Systems", tier: "B", domain: "交叉/综合/新兴", publisher: "IEEE" },
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
