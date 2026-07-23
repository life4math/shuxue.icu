// shuxue.icu 统一数据格式
// Schema: scripts/schema.json
// 最后更新: 2026-07-22T12:46:48.812626

const questions = [
  {
    "id": "Q001",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-02-02-01"
    ],
    "difficulty": 2,
    "type": "choice",
    "status": "approved",
    "stem": "已知函数 $f(x) = x^2 - 2ax + 3$ 在区间 $[1, +\\infty)$ 上单调递增，则实数 $a$ 的取值范围是",
    "options": [
      {
        "label": "A",
        "content": "$a \\leq 1$"
      },
      {
        "label": "B",
        "content": "$a \\geq 1$"
      },
      {
        "label": "C",
        "content": "$a \\leq -1$"
      },
      {
        "label": "D",
        "content": "$a \\geq -1$"
      }
    ],
    "answer": "A",
    "analysis": "函数 $f(x) = x^2 - 2ax + 3$ 的对称轴为 $x = a$。因为函数在 $[1, +\\infty)$ 上单调递增，所以对称轴 $a \\leq 1$。",
    "tags": [
      "单调性",
      "二次函数"
    ],
    "source": {
      "type": "真题",
      "year": 2023,
      "region": "全国I卷"
    },
    "stats": {
      "total": 156,
      "correct": 128,
      "accuracy": 82
    }
  },
  {
    "id": "Q002",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-02-02-02"
    ],
    "difficulty": 3,
    "type": "choice",
    "status": "approved",
    "stem": "已知函数 $f(x)$ 是定义在 $\\mathbb{R}$ 上的奇函数，当 $x > 0$ 时，$f(x) = x^2 - 2x + 3$，则 $f(-1) = $",
    "options": [
      {
        "label": "A",
        "content": "$-2$"
      },
      {
        "label": "B",
        "content": "$2$"
      },
      {
        "label": "C",
        "content": "$-6$"
      },
      {
        "label": "D",
        "content": "$6$"
      }
    ],
    "answer": "A",
    "analysis": "由奇函数性质：$f(-1) = -f(1)$。当 $x=1$ 时，$f(1) = 1 - 2 + 3 = 2$，所以 $f(-1) = -2$。",
    "tags": [
      "奇偶性",
      "函数求值"
    ],
    "source": {
      "type": "模拟",
      "year": 2024
    },
    "stats": {
      "total": 203,
      "correct": 156,
      "accuracy": 77
    }
  },
  {
    "id": "Q003",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-03-04"
    ],
    "difficulty": 3,
    "type": "fill",
    "status": "approved",
    "stem": "已知 $\\sin\\alpha + \\cos\\alpha = \\frac{1}{3}$，则 $\\sin 2\\alpha = $ ______。",
    "answer": "$-\\frac{8}{9}$",
    "analysis": "由 $(\\sin\\alpha + \\cos\\alpha)^2 = 1 + \\sin 2\\alpha = \\frac{1}{9}$，得 $\\sin 2\\alpha = \\frac{1}{9} - 1 = -\\frac{8}{9}$。",
    "tags": [
      "三角恒等变换",
      "二倍角"
    ],
    "source": {
      "type": "真题",
      "year": 2022,
      "region": "全国II卷"
    },
    "stats": {
      "total": 189,
      "correct": 98,
      "accuracy": 52
    }
  },
  {
    "id": "Q004",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-05-02"
    ],
    "difficulty": 4,
    "type": "solve",
    "status": "approved",
    "stem": "已知函数 $f(x) = x^3 - 3ax^2 + 3bx$ 在 $x = 1$ 处有极值 $-1$。\n(1) 求 $a, b$ 的值；\n(2) 求 $f(x)$ 的单调区间。",
    "answer": "(1) $a = 1, b = 0$; (2) 增区间 $(-\\infty, 0)$ 和 $(2, +\\infty)$，减区间 $(0, 2)$",
    "analysis": "(1) $f'(x) = 3x^2 - 6ax + 3b$，由 $f'(1) = 0$ 和 $f(1) = -1$ 联立求解。",
    "tags": [
      "导数",
      "极值",
      "单调性"
    ],
    "source": {
      "type": "真题",
      "year": 2024,
      "region": "全国I卷"
    },
    "stats": {
      "total": 234,
      "correct": 89,
      "accuracy": 38
    }
  },
  {
    "id": "Q005",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-04-04"
    ],
    "difficulty": 4,
    "type": "solve",
    "status": "approved",
    "stem": "已知数列 $\\{a_n\\}$ 的前 $n$ 项和 $S_n = n^2 + n$，求数列 $\\left\\{\\frac{1}{a_n a_{n+1}}\\right\\}$ 的前 $n$ 项和 $T_n$。",
    "answer": "$T_n = \\frac{n}{2(n+1)}$",
    "analysis": "先求 $a_n = 2n$，再利用裂项相消法求和。",
    "tags": [
      "数列",
      "裂项相消"
    ],
    "source": {
      "type": "模拟",
      "year": 2024
    },
    "stats": {
      "total": 178,
      "correct": 67,
      "accuracy": 38
    }
  },
  {
    "id": "Q006",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-01-02"
    ],
    "difficulty": 2,
    "type": "choice",
    "status": "approved",
    "stem": "已知向量 $\\vec{a} = (1, 2)$，$\\vec{b} = (3, -1)$，则 $\\vec{a} \\cdot \\vec{b} = $",
    "options": [
      {
        "label": "A",
        "content": "$1$"
      },
      {
        "label": "B",
        "content": "$5$"
      },
      {
        "label": "C",
        "content": "$-1$"
      },
      {
        "label": "D",
        "content": "$7$"
      }
    ],
    "answer": "A",
    "analysis": "$\\vec{a} \\cdot \\vec{b} = 1 \\times 3 + 2 \\times (-1) = 3 - 2 = 1$。",
    "tags": [
      "向量",
      "数量积"
    ],
    "source": {
      "type": "真题",
      "year": 2023,
      "region": "全国III卷"
    },
    "stats": {
      "total": 267,
      "correct": 241,
      "accuracy": 90
    }
  },
  {
    "id": "Q007",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-03-03"
    ],
    "difficulty": 4,
    "type": "choice",
    "status": "approved",
    "stem": "已知椭圆 $\\frac{x^2}{a^2} + \\frac{y^2}{b^2} = 1 (a > b > 0)$ 的离心率为 $\\frac{\\sqrt{3}}{2}$，短轴长为 $4$，则椭圆的标准方程为",
    "options": [
      {
        "label": "A",
        "content": "$\\frac{x^2}{16} + \\frac{y^2}{4} = 1$"
      },
      {
        "label": "B",
        "content": "$\\frac{x^2}{4} + \\frac{y^2}{16} = 1$"
      },
      {
        "label": "C",
        "content": "$\\frac{x^2}{8} + \\frac{y^2}{4} = 1$"
      },
      {
        "label": "D",
        "content": "$\\frac{x^2}{12} + \\frac{y^2}{4} = 1$"
      }
    ],
    "answer": "A",
    "analysis": "由 $2b = 4$ 得 $b = 2$，$e = \\frac{c}{a} = \\frac{\\sqrt{3}}{2}$，$c^2 = a^2 - b^2$，解得 $a^2 = 16$。",
    "tags": [
      "椭圆",
      "离心率"
    ],
    "source": {
      "type": "真题",
      "year": 2023,
      "region": "全国I卷"
    },
    "stats": {
      "total": 198,
      "correct": 112,
      "accuracy": 57
    }
  },
  {
    "id": "Q008",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-02-04"
    ],
    "difficulty": 4,
    "type": "solve",
    "status": "approved",
    "stem": "在三棱锥 $P-ABC$ 中，$PA \\perp$ 平面 $ABC$，$PA = AB = AC = 2$，$\\angle BAC = 120°$。\n(1) 证明：$BC \\perp$ 平面 $PAB$；\n(2) 求二面角 $P-BC-A$ 的余弦值。",
    "answer": "(1) 略; (2) $\\frac{\\sqrt{21}}{7}$",
    "analysis": "建立空间直角坐标系，利用空间向量法求解。",
    "tags": [
      "立体几何",
      "空间向量",
      "二面角"
    ],
    "source": {
      "type": "真题",
      "year": 2024,
      "region": "全国II卷"
    },
    "stats": {
      "total": 156,
      "correct": 45,
      "accuracy": 29
    }
  },
  {
    "id": "Q009",
    "module": "ALGE",
    "knowledge_points": [
      "ALGE-01-02"
    ],
    "difficulty": 3,
    "type": "fill",
    "status": "approved",
    "stem": "已知 $x > 0, y > 0$，且 $x + 2y = 1$，则 $\\frac{1}{x} + \\frac{1}{y}$ 的最小值为 ______。",
    "answer": "$3 + 2\\sqrt{2}$",
    "analysis": "利用基本不等式：$\\frac{1}{x} + \\frac{1}{y} = (\\frac{1}{x} + \\frac{1}{y})(x + 2y) = 3 + \\frac{2y}{x} + \\frac{x}{y} \\geq 3 + 2\\sqrt{2}$。",
    "tags": [
      "基本不等式",
      "最值"
    ],
    "source": {
      "type": "模拟",
      "year": 2024
    },
    "stats": {
      "total": 145,
      "correct": 82,
      "accuracy": 57
    }
  },
  {
    "id": "Q010",
    "module": "PROB",
    "knowledge_points": [
      "PROB-01-03"
    ],
    "difficulty": 4,
    "type": "solve",
    "status": "approved",
    "stem": "某工厂生产甲、乙两种产品，甲产品的一等品率为 $80\\%$，二等品率为 $20\\%$；乙产品的一等品率为 $75\\%$，二等品率为 $25\\%$。生产 1 件甲产品，若是一等品则获利润 4 万元，若是二等品则亏损 1 万元；生产 1 件乙产品，若是一等品则获利润 3 万元，若是二等品则亏损 2 万元。设生产甲产品 $x$ 件，乙产品 $y$ 件。\n(1) 求总利润的分布列和数学期望；\n(2) 若总利润不低于 10 万元的概率大于 $0.9$，求至少需要生产甲、乙产品各多少件。",
    "answer": "(1) 分布列略，$E = 3x + 1.75y$; (2) 根据实际情况讨论",
    "analysis": "利用期望公式和概率计算求解。",
    "tags": [
      "随机变量",
      "期望",
      "概率分布"
    ],
    "source": {
      "type": "真题",
      "year": 2023,
      "region": "全国I卷"
    },
    "stats": {
      "total": 167,
      "correct": 34,
      "accuracy": 20
    }
  },
  {
    "id": "Q011",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-03-03"
    ],
    "difficulty": 3,
    "type": "choice",
    "status": "approved",
    "stem": "函数 $f(x) = 2\\sin(\\omega x + \\varphi)$（$\\omega > 0$，$|\\varphi| < \\frac{\\pi}{2}$）的部分图象如图所示，则 $f(\\frac{\\pi}{4}) = $",
    "options": [
      {
        "label": "A",
        "content": "$-\\sqrt{3}$"
      },
      {
        "label": "B",
        "content": "$-1$"
      },
      {
        "label": "C",
        "content": "$1$"
      },
      {
        "label": "D",
        "content": "$\\sqrt{3}$"
      }
    ],
    "answer": "D",
    "analysis": "由图象确定 $\\omega = 2, \\varphi = \\frac{\\pi}{6}$，代入求值。",
    "tags": [
      "三角函数",
      "图象"
    ],
    "source": {
      "type": "真题",
      "year": 2022,
      "region": "全国I卷"
    },
    "stats": {
      "total": 210,
      "correct": 126,
      "accuracy": 60
    }
  },
  {
    "id": "Q012",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-05-04"
    ],
    "difficulty": 5,
    "type": "proof",
    "status": "approved",
    "stem": "已知函数 $f(x) = e^x - ax - 1$。\n(1) 讨论 $f(x)$ 的单调性；\n(2) 若 $f(x) \\geq 0$ 对 $x \\in \\mathbb{R}$ 恒成立，求 $a$ 的取值范围；\n(3) 证明：当 $a = 1$ 时，$e^x \\geq x + 1 + \\frac{x^2}{2}$（$x \\geq 0$）。",
    "answer": "(1) 当 $a \\leq 0$ 时在 $\\mathbb{R}$ 上递增，当 $a > 0$ 时在 $(-\\infty, \\ln a)$ 递减，$(\\ln a, +\\infty)$ 递增; (2) $a = 1$; (3) 构造函数求导证明",
    "analysis": "利用导数研究函数性质，分类讨论，构造辅助函数证明不等式。",
    "tags": [
      "导数",
      "不等式证明",
      "恒成立"
    ],
    "source": {
      "type": "真题",
      "year": 2024,
      "region": "全国I卷"
    },
    "stats": {
      "total": 189,
      "correct": 23,
      "accuracy": 12
    }
  },
  {
    "id": "Q013",
    "module": "PROB",
    "knowledge_points": [
      "PROB-02-01"
    ],
    "difficulty": 2,
    "type": "choice",
    "status": "approved",
    "stem": "某学校高一年级有 600 名学生，高二年级有 500 名学生，高三年级有 400 名学生。用分层抽样的方法从这三个年级中抽取 150 名学生进行体能测试，则应从高二年级抽取的学生人数为",
    "options": [
      {
        "label": "A",
        "content": "$40$"
      },
      {
        "label": "B",
        "content": "$50$"
      },
      {
        "label": "C",
        "content": "$60$"
      },
      {
        "label": "D",
        "content": "$75$"
      }
    ],
    "answer": "B",
    "analysis": "抽样比为 $\\frac{150}{1500} = \\frac{1}{10}$，高二应抽取 $500 \\times \\frac{1}{10} = 50$ 人。",
    "tags": [
      "分层抽样"
    ],
    "source": {
      "type": "真题",
      "year": 2023,
      "region": "全国II卷"
    },
    "stats": {
      "total": 234,
      "correct": 215,
      "accuracy": 92
    }
  },
  {
    "id": "Q014",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-03-06"
    ],
    "difficulty": 5,
    "type": "solve",
    "status": "approved",
    "stem": "已知椭圆 $C: \\frac{x^2}{4} + y^2 = 1$，过点 $P(0, 1)$ 的直线 $l$ 与椭圆交于 $A, B$ 两点。\n(1) 求 $|PA| \\cdot |PB|$ 的最大值；\n(2) 若 $OA \\perp OB$（$O$ 为坐标原点），求直线 $l$ 的方程。",
    "answer": "(1) $\\frac{5}{4}$; (2) $y = \\pm\\frac{\\sqrt{2}}{4}x + 1$",
    "analysis": "联立直线与椭圆方程，利用韦达定理和判别式求解。",
    "tags": [
      "椭圆",
      "直线",
      "韦达定理"
    ],
    "source": {
      "type": "真题",
      "year": 2024,
      "region": "全国I卷"
    },
    "stats": {
      "total": 145,
      "correct": 18,
      "accuracy": 12
    }
  },
  {
    "id": "Q015",
    "module": "ALGE",
    "knowledge_points": [
      "ALGE-03-01"
    ],
    "difficulty": 3,
    "type": "choice",
    "status": "approved",
    "stem": "从 6 名男同学和 4 名女同学中选出 3 人参加比赛，要求至少有 1 名女同学，则不同的选法共有",
    "options": [
      {
        "label": "A",
        "content": "$80$ 种"
      },
      {
        "label": "B",
        "content": "$100$ 种"
      },
      {
        "label": "C",
        "content": "$120$ 种"
      },
      {
        "label": "D",
        "content": "$160$ 种"
      }
    ],
    "answer": "B",
    "analysis": "$C_{10}^3 - C_6^3 = 120 - 20 = 100$ 种。",
    "tags": [
      "排列组合"
    ],
    "source": {
      "type": "模拟",
      "year": 2024
    },
    "stats": {
      "total": 178,
      "correct": 134,
      "accuracy": 75
    }
  },
  {
    "id": "Q016",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-02-03"
    ],
    "difficulty": 2,
    "type": "choice",
    "status": "approved",
    "stem": "已知 $a = 2^{0.3}$，$b = 0.3^2$，$c = \\log_2 0.3$，则 $a, b, c$ 的大小关系为",
    "options": [
      {
        "label": "A",
        "content": "$a > b > c$"
      },
      {
        "label": "B",
        "content": "$b > a > c$"
      },
      {
        "label": "C",
        "content": "$c > a > b$"
      },
      {
        "label": "D",
        "content": "$a > c > b$"
      }
    ],
    "answer": "A",
    "analysis": "$a = 2^{0.3} > 1$，$b = 0.09 < 1$，$c = \\log_2 0.3 < 0$。",
    "tags": [
      "指数函数",
      "对数函数",
      "比较大小"
    ],
    "source": {
      "type": "真题",
      "year": 2022,
      "region": "全国III卷"
    },
    "stats": {
      "total": 245,
      "correct": 208,
      "accuracy": 85
    }
  },
  {
    "id": "Q017",
    "module": "FUNC",
    "difficulty": 3,
    "type": "choice",
    "stem": "[模拟] 已知函数 $f(x) = x^2 - 2ax + 3$ 在 $x=1$ 处取极小值，求 $a$",
    "options": [
      {
        "label": "A",
        "content": "$1$"
      },
      {
        "label": "B",
        "content": "$2$"
      },
      {
        "label": "C",
        "content": "$3$"
      },
      {
        "label": "D",
        "content": "$4$"
      }
    ],
    "answer": "A",
    "analysis": "模拟解析",
    "tags": [
      "模拟",
      "二次函数"
    ],
    "knowledge_points": [
      "FUNC-02-02-01"
    ],
    "source": {
      "type": "自编",
      "year": 2024,
      "region": ""
    },
    "status": "active",
    "created_at": "2026-07-22T12:46:45.603491",
    "stats": {
      "total": 0,
      "correct": 0,
      "accuracy": 0
    },
    "related_methods": []
  }
];

const methods = [
  {
    "id": "M001",
    "name": "裂项相消法",
    "category": "数列求和",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-04-04"
    ],
    "applicable_types": [
      "fill",
      "solve"
    ],
    "difficulty_range": [
      3,
      5
    ],
    "keywords": [
      "数列",
      "求和",
      "裂项",
      "相消",
      "通项拆分"
    ],
    "principle": "将通项 $a_n$ 拆为两项之差 $f(n) - f(n+1)$，求和时中间项正负抵消，仅留首尾",
    "steps": [
      "识别通项结构，判断是否可拆为 $f(n) - f(n+1)$ 形式",
      "写出拆分后的 $a_n = f(n) - f(n+1)$",
      "展开求和 $S_n = (f(1)-f(2)) + (f(2)-f(3)) + \\cdots + (f(n)-f(n+1))$",
      "中间项抵消，得 $S_n = f(1) - f(n+1)$",
      "化简写出最终结果"
    ],
    "common_forms": [
      "$\\frac{1}{n(n+1)} = \\frac{1}{n} - \\frac{1}{n+1}$",
      "$\\frac{1}{(2n-1)(2n+1)} = \\frac{1}{2}(\\frac{1}{2n-1} - \\frac{1}{2n+1})$",
      "$\\frac{1}{\\sqrt{n}+\\sqrt{n+1}} = \\sqrt{n+1} - \\sqrt{n}$"
    ],
    "examples": [
      "Q005"
    ],
    "pitfalls": [
      "拆分系数易遗漏（如 $\\frac{1}{2}$ 前置系数）",
      "首尾项不一定恰好抵消，需单独验证"
    ]
  },
  {
    "id": "M002",
    "name": "构造辅助函数法",
    "category": "不等式证明",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-05-04"
    ],
    "applicable_types": [
      "solve",
      "proof"
    ],
    "difficulty_range": [
      4,
      5
    ],
    "keywords": [
      "导数",
      "不等式",
      "恒成立",
      "构造函数",
      "辅助函数"
    ],
    "principle": "将不等式转化为函数单调性/极值问题，构造 $g(x)$ 使得原不等式等价于 $g(x) \\geq 0$",
    "steps": [
      "观察不等式结构，确定构造目标：$g(x) \\geq 0$ 或 $g(x) \\leq 0$",
      "构造辅助函数 $g(x)$（移项使一侧为 0）",
      "求 $g'(x)$，分析 $g(x)$ 的单调性",
      "找到 $g(x)$ 的极值/最值点",
      "由最值推断 $g(x)$ 的符号，完成证明"
    ],
    "common_forms": [
      "$e^x \\geq x+1$ → 构造 $g(x)=e^x-x-1$",
      "$\\ln x \\leq x-1$ → 构造 $g(x)=\\ln x-x+1$",
      "$f(x) \\geq g(x)$ → 构造 $h(x)=f(x)-g(x)$"
    ],
    "examples": [
      "Q012"
    ],
    "pitfalls": [
      "构造方向错误（移项到哪一侧）",
      "忘记验证边界条件（$x=0$ 等）",
      "二次构造时忽略外层函数单调性"
    ]
  },
  {
    "id": "M003",
    "name": "韦达定理联立法",
    "category": "圆锥曲线",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-03-06"
    ],
    "applicable_types": [
      "solve"
    ],
    "difficulty_range": [
      4,
      5
    ],
    "keywords": [
      "椭圆",
      "双曲线",
      "抛物线",
      "韦达定理",
      "联立",
      "弦长",
      "点差法"
    ],
    "principle": "将直线方程代入曲线方程，利用韦达定理 $x_1+x_2, x_1 x_2$ 表示关系，避免求交点坐标",
    "steps": [
      "设直线方程 $y=kx+m$（或参数方程）",
      "代入曲线方程，整理为关于 $x$（或 $y$）的一元二次方程",
      "写出韦达定理：$x_1+x_2=-\\frac{b}{a}$, $x_1 x_2=\\frac{c}{a}$",
      "将目标表达式用 $x_1+x_2, x_1 x_2$ 表示",
      "消参求解"
    ],
    "common_forms": [
      "弦长 $|AB|=\\sqrt{1+k^2}|x_1-x_2|=\\sqrt{1+k^2}\\sqrt{(x_1+x_2)^2-4x_1 x_2}$",
      "面积 $S=\\frac{1}{2}|y_1-y_2| \\cdot d$",
      "$\\vec{OA} \\cdot \\vec{OB}=x_1 x_2 + y_1 y_2$"
    ],
    "examples": [
      "Q014"
    ],
    "pitfalls": [
      "忘记验证 $\\Delta > 0$（直线与曲线确实相交）",
      "计算量过大时考虑设点差法简化",
      "参数方程和普通方程混用出错"
    ]
  },
  {
    "id": "M004",
    "name": "空间向量坐标法",
    "category": "立体几何",
    "module": "GEOM",
    "knowledge_points": [
      "GEOM-02-04"
    ],
    "applicable_types": [
      "solve",
      "proof"
    ],
    "difficulty_range": [
      3,
      5
    ],
    "keywords": [
      "空间向量",
      "立体几何",
      "建系",
      "二面角",
      "线面角",
      "法向量"
    ],
    "principle": "建立空间直角坐标系，将几何问题转化为向量运算，用法向量求角度",
    "steps": [
      "观察几何体特征，选择合适的坐标系原点和轴方向",
      "写出关键点的坐标",
      "求相关平面的法向量 $\\vec{n}$（叉乘或待定系数法）",
      "用向量公式求角：线面角 $\\sin\\theta=\\frac{|\\vec{d} \\cdot \\vec{n}|}{|\\vec{d}||\\vec{n}|}$，二面角余弦",
      "判断角的锐钝性，写出最终结果"
    ],
    "common_forms": [
      "法向量：设 $\\vec{n}=(x,y,z)$，由 $\\vec{n} \\cdot \\vec{a}=0$ 且 $\\vec{n} \\cdot \\vec{b}=0$ 解出",
      "二面角：$\\cos\\theta=\\frac{\\vec{n_1} \\cdot \\vec{n_2}}{|\\vec{n_1}||\\vec{n_2}|}$",
      "线面角：$\\sin\\theta=\\frac{|\\vec{d} \\cdot \\vec{n}|}{|\\vec{d}||\\vec{n}|}$"
    ],
    "examples": [
      "Q008"
    ],
    "pitfalls": [
      "建系不当导致坐标复杂（优先利用垂直关系）",
      "二面角锐钝判断需看法向量方向",
      "证明线面垂直需要两个不共线方向"
    ]
  },
  {
    "id": "M005",
    "name": "分离参数法",
    "category": "恒成立问题",
    "module": "FUNC",
    "knowledge_points": [
      "FUNC-05-04",
      "FUNC-05-03"
    ],
    "applicable_types": [
      "solve",
      "fill"
    ],
    "difficulty_range": [
      3,
      5
    ],
    "keywords": [
      "恒成立",
      "参数范围",
      "分离参数",
      "最值",
      "存在性"
    ],
    "principle": "将含参不等式中的参数分离到一侧，转化为求另一侧函数的最值问题",
    "steps": [
      "识别含参不等式：$f(x,a) \\geq 0$ 对 $x \\in D$ 恒成立",
      "分离参数：$a \\geq g(x)$ 或 $a \\leq g(x)$（参数在一侧，不含 $a$ 的在另一侧）",
      "恒成立 → $a \\geq \\max g(x)$ 或 $a \\leq \\min g(x)$",
      "求 $g(x)$ 的最值（导数法）",
      "写出参数范围"
    ],
    "common_forms": [
      "$f(x) \\geq 0$ 恒成立 → $a \\geq f(x)/h(x)$ 的最大值",
      "$f(x) \\leq 0$ 恒成立 → $a \\leq f(x)/h(x)$ 的最小值",
      "存在性：$a \\geq \\min g(x)$ 或 $a \\leq \\max g(x)$"
    ],
    "examples": [
      "Q012"
    ],
    "pitfalls": [
      "分离时除式为 0 的情况需单独讨论",
      "不能分离时（参数出现在多处）需用端点效应或分类讨论",
      "存在性与恒成立的最大/最小值方向相反"
    ]
  },
  {
    "id": "M006",
    "name": "基本不等式配凑法",
    "category": "最值求解",
    "module": "ALGE",
    "knowledge_points": [
      "ALGE-01-02"
    ],
    "applicable_types": [
      "fill",
      "solve"
    ],
    "difficulty_range": [
      2,
      4
    ],
    "keywords": [
      "基本不等式",
      "最值",
      "配凑",
      "$1$ 的代换",
      "乘$1$法"
    ],
    "principle": "利用 $a+b \\geq 2\\sqrt{ab}$（或 $ab \\leq \\frac{(a+b)^2}{4}$）求最值，需满足'一正二定三相等'",
    "steps": [
      "识别求最值目标（和的最值或积的最值）",
      "检查条件是否满足'一正'（各项为正）",
      "配凑使'二定'（和定求积最大，积定求和最小）",
      "验证'三相等'（等号成立条件是否可达）",
      "写出最值及等号成立条件"
    ],
    "common_forms": [
      "乘$1$法：$\\frac{1}{x}+\\frac{1}{y}=(\\frac{1}{x}+\\frac{1}{y})(x+2y)$",
      "配凑系数：$x+\\frac{k}{x} \\geq 2\\sqrt{k}$",
      "权方和：$\\frac{a^2}{x}+\\frac{b^2}{y} \\geq \\frac{(a+b)^2}{x+y}$"
    ],
    "examples": [
      "Q009"
    ],
    "pitfalls": [
      "等号不成立时基本不等式失效，需用函数单调性",
      "多次使用不等式时等号条件需同时满足",
      "配凑方向选择错误（和定 vs 积定）"
    ]
  },
  {
    "id": "M007",
    "name": "[模拟] 配方法",
    "category": "二次函数",
    "module": "FUNC",
    "principle": "将 $ax^2+bx+c$ 化为 $a(x-h)^2+k$ 形式",
    "steps": [
      "提取 $a$",
      "配中项 $\\frac{b}{2a}$",
      "加减平衡",
      "写出顶点式"
    ],
    "keywords": [
      "二次函数",
      "配方"
    ],
    "applicable_types": [
      "fill",
      "solve"
    ],
    "difficulty_range": [
      2,
      4
    ],
    "common_forms": [
      "$ax^2+bx+c = a(x+\\frac{b}{2a})^2 + c-\\frac{b^2}{4a}$"
    ],
    "pitfalls": [
      "配方时忘记提取系数 $a$"
    ],
    "status": "active",
    "created_at": "2026-07-22T12:46:48.811862",
    "examples": []
  }
];

const reviewQueue = [
  {
    "id": "R001",
    "status": "pending",
    "source": "image_ocr",
    "sourceFile": "试卷_全国I卷_2024_第17题.png",
    "extractedAt": "2026-07-22T10:30:00",
    "data": {
      "module": "FUNC",
      "knowledge_points": [
        "FUNC-05-03"
      ],
      "difficulty": 4,
      "type": "solve",
      "stem": "已知函数 $f(x) = \\ln x - \\frac{1}{2}ax^2 + bx$，若 $f(x)$ 在 $x=1$ 处取极大值 $\\frac{1}{2}$。\n(1) 求 $a, b$ 的值；\n(2) 若 $f(x) \\leq \\frac{1}{2}$ 对 $x \\in (0, +\\infty)$ 恒成立，求 $a$ 的取值范围。",
      "options": [],
      "answer": "(1) $a=1, b=1$; (2) $a \\geq 1$",
      "analysis": "(1) $f'(1)=0$ 且 $f(1)=\\frac{1}{2}$ 解得 $a=1,b=1$；(2) 分离参数法或构造辅助函数证明",
      "tags": [
        "导数",
        "极值",
        "恒成立"
      ],
      "source": {
        "type": "真题",
        "year": 2024,
        "region": "全国I卷"
      }
    },
    "aiConfidence": 0.92,
    "reviewNotes": ""
  },
  {
    "id": "R002",
    "status": "pending",
    "source": "pdf_parse",
    "sourceFile": "教案_三角函数_2024秋.docx",
    "extractedAt": "2026-07-22T10:45:00",
    "data": {
      "module": "FUNC",
      "knowledge_points": [
        "FUNC-03-04"
      ],
      "difficulty": 3,
      "type": "fill",
      "stem": "已知 $\\tan\\alpha = 3$，则 $\\sin 2\\alpha + \\cos 2\\alpha = $ ______。",
      "options": [],
      "answer": "$\\frac{7}{5}$",
      "analysis": "$\\sin 2\\alpha = \\frac{2\\tan\\alpha}{1+\\tan^2\\alpha} = \\frac{6}{10}$，$\\cos 2\\alpha = \\frac{1-\\tan^2\\alpha}{1+\\tan^2\\alpha} = \\frac{-8}{10}$... 需复核",
      "tags": [
        "三角恒等变换",
        "二倍角"
      ],
      "source": {
        "type": "教案",
        "year": 2024
      }
    },
    "aiConfidence": 0.78,
    "reviewNotes": "公式识别可能有误，cos2α 符号需验证"
  },
  {
    "id": "R003",
    "status": "pending",
    "source": "image_ocr",
    "sourceFile": "笔记_数列求和方法.jpg",
    "extractedAt": "2026-07-22T11:00:00",
    "data": {
      "module": "FUNC",
      "knowledge_points": [
        "FUNC-04-04"
      ],
      "difficulty": 4,
      "type": "solve",
      "stem": "已知数列 $\\{a_n\\}$ 满足 $a_1 = 1$，$a_{n+1} = \\frac{n+1}{n}a_n$，求 $\\sum_{k=1}^{n} \\frac{1}{a_k}$。",
      "options": [],
      "answer": "$\\frac{n(n+1)}{2}$",
      "analysis": "先求 $a_n = n$，再 $\\sum \\frac{1}{n}$ ... 需复核裂项过程",
      "tags": [
        "数列",
        "裂项相消"
      ],
      "source": {
        "type": "手写笔记"
      }
    },
    "aiConfidence": 0.85,
    "reviewNotes": "手写识别，答案可能有误"
  }
];

const knowledgeTree = [
  {
    id: "FUNC", name: "函数与导数", level: 1, expanded: true,
    children: [
      {
        id: "FUNC-01", name: "集合与常用逻辑用语", level: 2,
        children: [
          { id: "FUNC-01-01", name: "集合的概念与运算", level: 3, difficulty: [1, 2], examFrequency: "high" },
          { id: "FUNC-01-02", name: "充分条件与必要条件", level: 3, difficulty: [2, 3], examFrequency: "medium" }
        ]
      },
      {
        id: "FUNC-02", name: "函数的概念与基本初等函数", level: 2,
        children: [
          { id: "FUNC-02-01", name: "函数的概念与表示", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "FUNC-02-02", name: "函数的基本性质", level: 3, difficulty: [2, 4], examFrequency: "high",
            children: [
              { id: "FUNC-02-02-01", name: "单调性", level: 4, difficulty: [2, 4], examFrequency: "high" },
              { id: "FUNC-02-02-02", name: "奇偶性", level: 4, difficulty: [2, 4], examFrequency: "high" },
              { id: "FUNC-02-02-03", name: "周期性", level: 4, difficulty: [3, 4], examFrequency: "medium" },
              { id: "FUNC-02-02-04", name: "对称性", level: 4, difficulty: [3, 5], examFrequency: "medium" }
            ]
          },
          { id: "FUNC-02-03", name: "幂函数、指数函数、对数函数", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "FUNC-02-04", name: "函数的图象", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "FUNC-02-05", name: "函数与方程", level: 3, difficulty: [3, 4], examFrequency: "medium" },
          { id: "FUNC-02-06", name: "函数模型及其应用", level: 3, difficulty: [2, 3], examFrequency: "low" }
        ]
      },
      {
        id: "FUNC-03", name: "三角函数与解三角形", level: 2,
        children: [
          { id: "FUNC-03-01", name: "任意角和弧度制", level: 3, difficulty: [1, 2], examFrequency: "medium" },
          { id: "FUNC-03-02", name: "三角函数的定义", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "FUNC-03-03", name: "三角函数的图象与性质", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "FUNC-03-04", name: "三角恒等变换", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "FUNC-03-05", name: "解三角形", level: 3, difficulty: [3, 4], examFrequency: "high" }
        ]
      },
      {
        id: "FUNC-04", name: "数列", level: 2,
        children: [
          { id: "FUNC-04-01", name: "数列的概念", level: 3, difficulty: [1, 2], examFrequency: "medium" },
          { id: "FUNC-04-02", name: "等差数列", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "FUNC-04-03", name: "等比数列", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "FUNC-04-04", name: "数列求和", level: 3, difficulty: [3, 5], examFrequency: "high" }
        ]
      },
      {
        id: "FUNC-05", name: "导数及其应用", level: 2,
        children: [
          { id: "FUNC-05-01", name: "导数的概念与运算", level: 3, difficulty: [2, 3], examFrequency: "high" },
          { id: "FUNC-05-02", name: "导数与函数的单调性", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "FUNC-05-03", name: "导数与函数的极值、最值", level: 3, difficulty: [3, 5], examFrequency: "high" },
          { id: "FUNC-05-04", name: "导数的综合应用", level: 3, difficulty: [4, 5], examFrequency: "high" }
        ]
      }
    ]
  },
  {
    id: "GEOM", name: "几何与向量", level: 1, expanded: false,
    children: [
      {
        id: "GEOM-01", name: "平面向量", level: 2,
        children: [
          { id: "GEOM-01-01", name: "向量的概念与线性运算", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "GEOM-01-02", name: "向量的数量积", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "GEOM-01-03", name: "向量的应用", level: 3, difficulty: [3, 4], examFrequency: "medium" }
        ]
      },
      {
        id: "GEOM-02", name: "立体几何", level: 2,
        children: [
          { id: "GEOM-02-01", name: "空间几何体", level: 3, difficulty: [2, 3], examFrequency: "medium" },
          { id: "GEOM-02-02", name: "空间点线面位置关系", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "GEOM-02-03", name: "空间向量及其运算", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "GEOM-02-04", name: "空间向量在立体几何中的应用", level: 3, difficulty: [3, 5], examFrequency: "high" }
        ]
      },
      {
        id: "GEOM-03", name: "解析几何", level: 2,
        children: [
          { id: "GEOM-03-01", name: "直线与方程", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "GEOM-03-02", name: "圆与方程", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "GEOM-03-03", name: "椭圆", level: 3, difficulty: [3, 5], examFrequency: "high" },
          { id: "GEOM-03-04", name: "双曲线", level: 3, difficulty: [3, 5], examFrequency: "high" },
          { id: "GEOM-03-05", name: "抛物线", level: 3, difficulty: [3, 5], examFrequency: "high" },
          { id: "GEOM-03-06", name: "直线与圆锥曲线的位置关系", level: 3, difficulty: [4, 5], examFrequency: "high" }
        ]
      }
    ]
  },
  {
    id: "ALGE", name: "代数与不等式", level: 1, expanded: false,
    children: [
      {
        id: "ALGE-01", name: "不等式", level: 2,
        children: [
          { id: "ALGE-01-01", name: "不等式的性质与解法", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "ALGE-01-02", name: "基本不等式", level: 3, difficulty: [2, 4], examFrequency: "high" },
          { id: "ALGE-01-03", name: "线性规划", level: 3, difficulty: [2, 3], examFrequency: "medium" }
        ]
      },
      {
        id: "ALGE-02", name: "复数", level: 2,
        children: [
          { id: "ALGE-02-01", name: "复数的概念与运算", level: 3, difficulty: [1, 2], examFrequency: "high" }
        ]
      },
      {
        id: "ALGE-03", name: "计数原理与二项式定理", level: 2,
        children: [
          { id: "ALGE-03-01", name: "排列与组合", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "ALGE-03-02", name: "二项式定理", level: 3, difficulty: [2, 4], examFrequency: "high" }
        ]
      }
    ]
  },
  {
    id: "PROB", name: "概率与统计", level: 1, expanded: false,
    children: [
      {
        id: "PROB-01", name: "概率", level: 2,
        children: [
          { id: "PROB-01-01", name: "古典概型与几何概型", level: 3, difficulty: [2, 3], examFrequency: "high" },
          { id: "PROB-01-02", name: "条件概率与独立性", level: 3, difficulty: [3, 4], examFrequency: "high" },
          { id: "PROB-01-03", name: "离散型随机变量及其分布", level: 3, difficulty: [3, 5], examFrequency: "high" },
          { id: "PROB-01-04", name: "正态分布", level: 3, difficulty: [2, 3], examFrequency: "medium" }
        ]
      },
      {
        id: "PROB-02", name: "统计", level: 2,
        children: [
          { id: "PROB-02-01", name: "抽样方法与数据特征", level: 3, difficulty: [1, 3], examFrequency: "high" },
          { id: "PROB-02-02", name: "回归分析与独立性检验", level: 3, difficulty: [2, 4], examFrequency: "medium" }
        ]
      }
    ]
  },
  {
    id: "CALC", name: "微积分初步", level: 1, expanded: false,
    children: [
      {
        id: "CALC-01", name: "微积分基础", level: 2,
        children: [
          { id: "CALC-01-01", name: "定积分的概念", level: 3, difficulty: [2, 3], examFrequency: "low" },
          { id: "CALC-01-02", name: "微积分基本定理", level: 3, difficulty: [2, 4], examFrequency: "low" }
        ]
      }
    ]
  }
];

const students = [
  {
    id: "S001", name: "张明", class: "高三(1)班",
    totalQuestions: 156, accuracy: 72, avgTime: 85, coveredPoints: 42, totalPoints: 52,
    moduleScores: [
      { module: "函数与导数", score: 78, level: "partial", count: 45, accuracy: 74 },
      { module: "几何与向量", score: 65, level: "partial", count: 32, accuracy: 63 },
      { module: "代数与不等式", score: 85, level: "mastered", count: 28, accuracy: 86 },
      { module: "概率与统计", score: 52, level: "unmastered", count: 25, accuracy: 48 },
      { module: "微积分初步", score: 70, level: "partial", count: 8, accuracy: 75 }
    ],
    weakPoints: [
      { id: "PROB-01-03", name: "离散型随机变量及其分布", module: "概率与统计", score: 35, level: "unmastered", priority: "P0", consecutiveErrors: 3, reason: "期望方差公式运用不熟练，分布列构建能力薄弱" },
      { id: "GEOM-03-06", name: "直线与圆锥曲线的位置关系", module: "几何与向量", score: 42, level: "unmastered", priority: "P0", consecutiveErrors: 4, reason: "联立方程后韦达定理运用不熟练，计算量大易出错" },
      { id: "FUNC-05-04", name: "导数的综合应用", module: "函数与导数", score: 48, level: "unmastered", priority: "P1", consecutiveErrors: 2, reason: "恒成立问题分类讨论不清晰，构造函数能力不足" },
      { id: "GEOM-02-04", name: "空间向量在立体几何中的应用", module: "几何与向量", score: 55, level: "partial", priority: "P1", consecutiveErrors: 0, reason: "空间想象能力不足，坐标系建立不够灵活" },
      { id: "FUNC-03-04", name: "三角恒等变换", module: "函数与导数", score: 62, level: "partial", priority: "P2", consecutiveErrors: 0, reason: "公式记忆不牢，和差化积运用不灵活" }
    ],
    accuracyTrend: [
      { date: "06-15", accuracy: 58 }, { date: "06-16", accuracy: 62 },
      { date: "06-17", accuracy: 65 }, { date: "06-18", accuracy: 60 },
      { date: "06-19", accuracy: 68 }, { date: "06-20", accuracy: 72 },
      { date: "06-21", accuracy: 70 }, { date: "06-22", accuracy: 75 },
      { date: "06-23", accuracy: 72 }, { date: "06-24", accuracy: 78 },
      { date: "06-25", accuracy: 74 }, { date: "06-26", accuracy: 76 },
      { date: "06-27", accuracy: 80 }, { date: "06-28", accuracy: 72 }
    ],
    difficultyAccuracy: [
      { difficulty: 1, label: "基础", count: 32, accuracy: 94 },
      { difficulty: 2, label: "简单", count: 45, accuracy: 82 },
      { difficulty: 3, label: "中等", count: 42, accuracy: 68 },
      { difficulty: 4, label: "较难", count: 25, accuracy: 48 },
      { difficulty: 5, label: "困难", count: 12, accuracy: 22 }
    ],
    recentRecords: [
      { questionId: "Q001", date: "06-28", correct: true, time: 65 },
      { questionId: "Q003", date: "06-28", correct: false, time: 120 },
      { questionId: "Q006", date: "06-27", correct: true, time: 45 },
      { questionId: "Q007", date: "06-27", correct: false, time: 180 },
      { questionId: "Q004", date: "06-26", correct: false, time: 420 },
      { questionId: "Q009", date: "06-26", correct: true, time: 150 },
      { questionId: "Q011", date: "06-25", correct: true, time: 90 },
      { questionId: "Q013", date: "06-25", correct: true, time: 40 },
      { questionId: "Q010", date: "06-24", correct: false, time: 380 },
      { questionId: "Q015", date: "06-24", correct: true, time: 75 }
    ]
  },
  {
    id: "S002", name: "李思雨", class: "高三(1)班",
    totalQuestions: 203, accuracy: 85, avgTime: 72, coveredPoints: 48, totalPoints: 52,
    moduleScores: [
      { module: "函数与导数", score: 88, level: "mastered", count: 58, accuracy: 88 },
      { module: "几何与向量", score: 82, level: "mastered", count: 45, accuracy: 80 },
      { module: "代数与不等式", score: 92, level: "mastered", count: 35, accuracy: 91 },
      { module: "概率与统计", score: 78, level: "partial", count: 38, accuracy: 79 },
      { module: "微积分初步", score: 85, level: "mastered", count: 12, accuracy: 83 }
    ],
    weakPoints: [
      { id: "FUNC-05-04", name: "导数的综合应用", module: "函数与导数", score: 68, level: "partial", priority: "P1", consecutiveErrors: 1, reason: "压轴题最后一问完成度不高" },
      { id: "PROB-01-03", name: "离散型随机变量及其分布", module: "概率与统计", score: 72, level: "partial", priority: "P2", consecutiveErrors: 0, reason: "超几何分布与二项分布区分不清" }
    ],
    accuracyTrend: [
      { date: "06-15", accuracy: 78 }, { date: "06-16", accuracy: 82 },
      { date: "06-17", accuracy: 80 }, { date: "06-18", accuracy: 85 },
      { date: "06-19", accuracy: 83 }, { date: "06-20", accuracy: 86 },
      { date: "06-21", accuracy: 84 }, { date: "06-22", accuracy: 88 },
      { date: "06-23", accuracy: 85 }, { date: "06-24", accuracy: 87 },
      { date: "06-25", accuracy: 86 }, { date: "06-26", accuracy: 89 },
      { date: "06-27", accuracy: 85 }, { date: "06-28", accuracy: 88 }
    ],
    difficultyAccuracy: [
      { difficulty: 1, label: "基础", count: 42, accuracy: 98 },
      { difficulty: 2, label: "简单", count: 58, accuracy: 93 },
      { difficulty: 3, label: "中等", count: 52, accuracy: 82 },
      { difficulty: 4, label: "较难", count: 35, accuracy: 68 },
      { difficulty: 5, label: "困难", count: 16, accuracy: 45 }
    ],
    recentRecords: []
  },
  {
    id: "S003", name: "王浩然", class: "高三(1)班",
    totalQuestions: 89, accuracy: 58, avgTime: 105, coveredPoints: 28, totalPoints: 52,
    moduleScores: [
      { module: "函数与导数", score: 55, level: "partial", count: 28, accuracy: 54 },
      { module: "几何与向量", score: 48, level: "unmastered", count: 20, accuracy: 45 },
      { module: "代数与不等式", score: 72, level: "partial", count: 18, accuracy: 72 },
      { module: "概率与统计", score: 42, level: "unmastered", count: 15, accuracy: 40 },
      { module: "微积分初步", score: 60, level: "partial", count: 5, accuracy: 60 }
    ],
    weakPoints: [
      { id: "GEOM-03-03", name: "椭圆", module: "几何与向量", score: 30, level: "unmastered", priority: "P0", consecutiveErrors: 5, reason: "椭圆基本性质不熟悉，焦点弦公式不会用" },
      { id: "PROB-01-01", name: "古典概型与几何概型", module: "概率与统计", score: 38, level: "unmastered", priority: "P0", consecutiveErrors: 3, reason: "基本事件空间构建不完整" },
      { id: "FUNC-03-03", name: "三角函数的图象与性质", module: "函数与导数", score: 45, level: "unmastered", priority: "P1", consecutiveErrors: 2, reason: "图象平移变换规律掌握不牢" },
      { id: "GEOM-01-02", name: "向量的数量积", module: "几何与向量", score: 52, level: "partial", priority: "P1", consecutiveErrors: 1, reason: "向量夹角公式运用不灵活" },
      { id: "FUNC-02-02", name: "函数的基本性质", module: "函数与导数", score: 58, level: "partial", priority: "P2", consecutiveErrors: 0, reason: "抽象函数性质推导能力弱" }
    ],
    accuracyTrend: [
      { date: "06-15", accuracy: 45 }, { date: "06-16", accuracy: 48 },
      { date: "06-17", accuracy: 52 }, { date: "06-18", accuracy: 50 },
      { date: "06-19", accuracy: 55 }, { date: "06-20", accuracy: 58 },
      { date: "06-21", accuracy: 54 }, { date: "06-22", accuracy: 60 },
      { date: "06-23", accuracy: 58 }, { date: "06-24", accuracy: 62 },
      { date: "06-25", accuracy: 60 }, { date: "06-26", accuracy: 58 },
      { date: "06-27", accuracy: 62 }, { date: "06-28", accuracy: 65 }
    ],
    difficultyAccuracy: [
      { difficulty: 1, label: "基础", count: 22, accuracy: 82 },
      { difficulty: 2, label: "简单", count: 28, accuracy: 64 },
      { difficulty: 3, label: "中等", count: 22, accuracy: 45 },
      { difficulty: 4, label: "较难", count: 12, accuracy: 25 },
      { difficulty: 5, label: "困难", count: 5, accuracy: 10 }
    ],
    recentRecords: []
  }
];

// --- 博客文章 ---
const blogPosts = [
  {
    id: "P001",
    title: "深入理解 React 18 并发渲染机制",
    slug: "react-18-concurrent-rendering",
    excerpt: "React 18 引入了并发渲染特性，从根本上改变了 React 的渲染方式。本文将深入剖析 Concurrent Mode、Suspense、自动批处理等核心机制。",
    content: "# 深入理解 React 18 并发渲染机制\n\nReact 18 引入了并发渲染（Concurrent Rendering）特性，这是 React 自 Hooks 以来最大的一次架构升级。\n\n## 什么是并发渲染\n\n并发渲染允许 React 在渲染过程中中断、暂停甚至放弃渲染任务。这意味着 React 可以优先处理更重要的更新。\n\n```jsx\nimport { createRoot } from 'react-dom/client'\nconst root = createRoot(document.getElementById('root'))\nroot.render(<App />)\n```\n\n## 核心特性\n\n### 自动批处理\n\nReact 18 之前，只有在事件处理函数中的状态更新会被批处理。现在 Promise、setTimeout 等异步回调中的更新也会自动批处理。\n\n### Suspense 改进\n\nSuspense 组件支持并发渲染下的数据获取，支持嵌套使用。\n\n### Transitions\n\n`startTransition` 允许将某些更新标记为\"非紧急\"，紧急更新可以立即响应。\n\n## 性能影响\n\n- 更流畅的交互体验\n- 更好的数据获取模式\n- 更智能的渲染调度\n\n## 总结\n\n理解 React 18 并发渲染的底层机制，有助于编写更高效的 React 应用。",
    tags: ["React", "JavaScript", "前端架构"],
    category: "前端框架",
    date: "2025-06-15",
    readTime: 8,
    label: "[JS]"
  },
  {
    id: "P002",
    title: "TypeScript 5.0 装饰器完全指南",
    slug: "typescript-5-decorators",
    excerpt: "TypeScript 5.0 终于带来了符合 ECMA 规范的装饰器。本文详细介绍新装饰器的语法、用法以及与旧版装饰器的区别。",
    content: "# TypeScript 5.0 装饰器完全指南\n\nTypeScript 5.0 引入了全新的装饰器实现，完全符合 ECMAScript 规范。\n\n## 新旧装饰器对比\n\n旧版需要 `experimentalDecorators: true`，新版有更清晰的类型推导和更好的标准化支持。\n\n## 装饰器类型\n\n- **类装饰器** — `ClassDecoratorContext`\n- **方法装饰器** — `ClassMethodDecoratorContext`\n- **属性装饰器 + Auto-Accessor** — `ClassAccessorDecoratorContext`\n\n## 元数据支持\n\n新版装饰器可以通过 `context.metadata` 存储和读取元数据。\n\n## 总结\n\nTypeScript 5.0 装饰器提供了更清晰的类型推导、更好的标准化支持，与 JavaScript 生态更好兼容。",
    tags: ["TypeScript", "JavaScript", "前端架构"],
    category: "编程语言",
    date: "2025-05-28",
    readTime: 10,
    label: "[TS]"
  },
  {
    id: "P003",
    title: "从零搭建 Vite + React + Tailwind 工程化体系",
    slug: "vite-react-tailwind-setup",
    excerpt: "一站式前端工程化搭建指南：Vite 构建、React 开发、Tailwind CSS 样式、ESLint + Prettier 代码规范全覆盖。",
    content: "# 从零搭建 Vite + React + Tailwind 工程化体系\n\n## 项目初始化\n\n```bash\nnpm create vite@latest my-app -- --template react-ts\ncd my-app && npm install\n```\n\n## 安装 Tailwind CSS\n\n```bash\nnpm install -D tailwindcss postcss autoprefixer\nnpx tailwindcss init -p\n```\n\n## 代码规范：ESLint + Prettier\n\n配置 `.eslintrc.cjs`，添加 Prettier 集成。\n\n## Git Hooks：Husky + lint-staged\n\n```bash\nnpm install -D husky lint-staged\nnpx husky init\n```\n\n## 路径别名\n\n在 `vite.config.ts` 中配置 `@` 别名。\n\n## 总结\n\n完善的工程化体系包含构建工具、样式方案、代码规范、Git Hooks 和路径别名。",
    tags: ["Vite", "React", "Tailwind CSS", "工程化"],
    category: "工程化",
    date: "2025-05-10",
    readTime: 12,
    label: "[VD]"
  },
  {
    id: "P004",
    title: "WebAssembly 性能实战：Rust + WASM 加速前端计算",
    slug: "wasm-rust-performance",
    excerpt: "当 JavaScript 性能遇上瓶颈时，WebAssembly 是最好的选择。本文通过实际案例展示如何用 Rust 编写 WASM 模块。",
    content: "# WebAssembly 性能实战：Rust + WASM 加速前端计算\n\n## 为什么需要 WebAssembly\n\nJavaScript 是解释型语言，在计算密集型任务时性能不足。WASM 提供接近原生的执行速度。\n\n## 安装 Rust 工具链\n\n```bash\ncurl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh\nrustup target add wasm32-unknown-unknown\n```\n\n## 编写 Rust 模块\n\n```rust\n#[no_mangle]\npub extern \"C\" fn fibonacci(n: u32) -> u64 {\n  // iterative implementation\n}\n```\n\n## 前端集成\n\n使用 `wasm-bindgen` 简化互操作。\n\n## 性能对比\n\n| 实现方式 | 耗时 |\n|---------|------|\n| JavaScript | ~12000ms |\n| WebAssembly | ~3500ms |\n\nWASM 比纯 JS 快约 3.4 倍。\n\n## 总结\n\nRust + WASM 是当前前端性能优化的最佳方案之一。",
    tags: ["WebAssembly", "Rust", "性能优化"],
    category: "性能优化",
    date: "2025-04-20",
    readTime: 15,
    label: "[WA]"
  },
  {
    id: "P005",
    title: "CSS Container Queries 实战指南",
    slug: "css-container-queries",
    excerpt: "Container Queries 彻底改变了响应式设计的范式。不再依赖视口宽度，而是基于容器尺寸进行适配。",
    content: "# CSS Container Queries 实战指南\n\n## 基本用法\n\n```css\n.card-container { container-type: inline-size; }\n```\n\n然后使用 `@container` 查询。\n\n## 与 Media Queries 的区别\n\n- Media Queries：基于视口尺寸\n- Container Queries：基于容器尺寸\n\n## 容器查询单位\n\n`cqw` `cqh` `cqi` `cqb` `cqmin` `cqmax`\n\n## 实战示例：自适应卡片组件\n\n不同容器宽度下卡片自动切换布局。\n\n## 浏览器兼容性\n\nChrome 105+、Firefox 110+、Safari 16+ 全支持。\n\n## 总结\n\nContainer Queries 是响应式设计的未来。",
    tags: ["CSS", "响应式设计", "前端开发"],
    category: "样式与设计",
    date: "2025-04-05",
    readTime: 7,
    label: "[CSS]"
  },
  {
    id: "P006",
    title: "Node.js 流式处理：高效处理大文件与数据管道",
    slug: "nodejs-streams-guide",
    excerpt: "Stream 是 Node.js 最强大的特性之一。深入讲解 Readable、Writable、Transform 流的用法。",
    content: "# Node.js 流式处理：高效处理大文件与数据管道\n\n## 四种流类型\n\n1. Readable — 可读流\n2. Writable — 可写流\n3. Duplex — 双工流\n4. Transform — 转换流\n\n## 读取大文件\n\n```javascript\nimport { createReadStream } from 'fs'\nconst stream = createReadStream('large-file.txt', { highWaterMark: 64 * 1024 })\n```\n\n## 管道（Pipeline）\n\n```javascript\nimport { pipeline } from 'stream/promises'\nawait pipeline(createReadStream('input.txt'), gzip(), createWriteStream('output.txt.gz'))\n```\n\n## 自定义 Transform 流\n\n实现 `_transform` 和 `_flush` 方法。\n\n## 背压（Backpressure）\n\n使用 `pipe` 或 `pipeline` 正确处理背压。\n\n## 总结\n\n掌握流式处理，可高效处理 GB 级数据而内存占用仅几 MB。",
    tags: ["Node.js", "后端开发", "性能优化"],
    category: "后端开发",
    date: "2025-03-18",
    readTime: 11,
    label: "[NODE]"
  },
  {
    id: "P007",
    title: "Docker Compose 多服务编排最佳实践",
    slug: "docker-compose-best-practices",
    excerpt: "从单容器到多服务编排：Docker Compose 实战指南，涵盖网络配置、数据持久化、健康检查等核心主题。",
    content: "# Docker Compose 多服务编排最佳实践\n\n## 基础结构\n\n```yaml\nversion: '3.9'\nservices:\n  web:\n    build: .\n    ports: [\"3000:3000\"]\n    depends_on:\n      db: { condition: service_healthy }\n  db:\n    image: postgres:16-alpine\n```\n\n## 环境变量管理\n\n使用 `.env` 文件管理敏感信息。\n\n## 多环境配置\n\nOverride 文件：`docker-compose.dev.yml` / `docker-compose.prod.yml`。\n\n## 网络隔离\n\n`frontend` + `backend` 双网络架构。\n\n## 健康检查与依赖\n\n`healthcheck` + `depends_on: condition: service_healthy`。\n\n## 资源限制\n\n`deploy.resources.limits` 控制 CPU 和内存。\n\n## 总结\n\nDocker Compose 配合合理配置策略，完全可以用于中小规模的生产部署。",
    tags: ["Docker", "DevOps", "后端开发"],
    category: "DevOps",
    date: "2025-03-01",
    readTime: 13,
    label: "[DK]"
  },
  {
    id: "P008",
    title: "GraphQL 与 REST API 设计对比：何时选择什么",
    slug: "graphql-vs-rest",
    excerpt: "GraphQL 是 REST 的替代品吗？本文从实际项目角度对比两者优缺点，帮助你在不同场景做出正确选择。",
    content: "# GraphQL 与 REST API 设计对比\n\n## 核心差异\n\n| 维度 | REST | GraphQL |\n|------|------|--------|\n| 数据获取 | 多端点固定结构 | 单端点按需查询 |\n| 版本管理 | URL版本 | 无需版本 |\n| 过度获取 | 常见 | 可避免 |\n\n## 何时选择 REST\n\n1. 简单 CRUD 应用\n2. 需要 HTTP 缓存\n3. 文件上传下载\n4. 微服务间通信\n\n## 何时选择 GraphQL\n\n1. 复杂关联数据\n2. 多端客户端\n3. 频繁变化 API\n4. 减少网络请求\n5. 实时数据 Subscriptions\n\n## 混合方案\n\n```javascript\napp.post('/api/upload', uploadHandler)  // REST\napp.use('/graphql', graphqlHTTP({ schema }))  // GraphQL\n```\n\n## 总结\n\n没有银弹。根据项目特点选择合适方案，甚至混合使用。",
    tags: ["GraphQL", "REST API", "后端开发"],
    category: "后端开发",
    date: "2025-02-15",
    readTime: 9,
    label: "[API]"
  }
];

// --- 工具函数 ---
function getAllKnowledgePoints(tree) {
  const result = [];
  function walk(nodes) {
    for (const node of nodes) {
      result.push({ id: node.id, name: node.name, level: node.level, module: node.module || node.id.split('-')[0] });
      if (node.children) walk(node.children);
    }
  }
  walk(tree);
  return result;
}

function getModuleName(id) {
  const names = { FUNC: "函数与导数", GEOM: "几何与向量", ALGE: "代数与不等式", PROB: "概率与统计", CALC: "微积分初步" };
  return names[id] || id;
}

function getDifficultyLabel(d) {
  return ["", "基础", "简单", "中等", "较难", "困难"][d] || d;
}

function getDifficultyColor(d) {
  return ["", currentTheme.difficulty[0], currentTheme.difficulty[1], currentTheme.difficulty[2], currentTheme.difficulty[3], currentTheme.difficulty[4]][d] || "#6e6e73";
}

function getTypeLabel(t) {
  const labels = { choice: "选择题", fill: "填空题", solve: "解答题", proof: "证明题" };
  return labels[t] || t;
}

function getLevelLabel(l) {
  const labels = { mastered: "已掌握", partial: "部分掌握", unmastered: "未掌握" };
  return labels[l] || l;
}

function getLevelColor(l) {
  return currentTheme.level[l] || "#6e6e73";
}

function getPriorityLabel(p) {
  const labels = { P0: "紧急", P1: "重要", P2: "关注" };
  return labels[p] || p;
}

function getPriorityColor(p) {
  return currentTheme.priority[p] || "#6e6e73";
}

function setThemeColors(theme) {
  // Called by themes.js applyTheme() — color functions read from currentTheme directly
}

/* ===== Subscription Tiers ===== */
const SUBSCRIPTION_TIERS = {
  free: {
    name: 'FREE', label: '教研入门',
    priceMonthly: 0, priceYearly: 0,
    limits: {
      questionsPerDay: 10, analyticsPerMonth: 3,
      uploadsPerDay: 1, aiReview: false, dataExport: false,
      methodCreate: false, knowledgeAnnotation: false,
      blogDraft: false, teamCollab: false
    },
    features: ['题库浏览 10题/日', '知识图谱 仅查看', '学情分析 3次/月', 'Blog 完整访问']
  },
  pro: {
    name: 'PRO', label: 'AI 驱动教研',
    priceMonthly: 49, priceYearly: 490,
    limits: {
      questionsPerDay: Infinity, analyticsPerMonth: Infinity,
      uploadsPerDay: 10, aiReview: true, dataExport: true,
      methodCreate: true, knowledgeAnnotation: true,
      blogDraft: true, teamCollab: false
    },
    features: ['题库无限', 'AI 审核 无限+优先', '学情分析 无限+PDF', '数据导出 CSV+PDF']
  },
  team: {
    name: 'TEAM', label: '教研组协作',
    priceMonthly: 199, priceYearly: 1990,
    seats: 5, extraSeatPrice: 39, maxSeats: 20,
    limits: {
      questionsPerDay: Infinity, analyticsPerMonth: Infinity,
      uploadsPerDay: Infinity, aiReview: true, dataExport: true,
      methodCreate: true, knowledgeAnnotation: true,
      blogDraft: true, teamCollab: true
    },
    features: ['Pro 全功能', '共享题库', '组级分析仪表盘', '24h 优先支持']
  },
  api: {
    name: 'API', label: '数据服务',
    priceMonthly: 500, priceYearly: 5000,
    limits: {
      questionsPerDay: Infinity, analyticsPerMonth: Infinity,
      uploadsPerDay: 0, aiReview: false, dataExport: true,
      methodCreate: false, knowledgeAnnotation: false,
      blogDraft: false, teamCollab: false,
      restfulApi: true, dataPackage: true
    },
    features: ['RESTful API', '结构化 JSON', '脱敏数据包', 'SLA 99.5%']
  }
};

/* ===== Current User Tier (demo: defaults to 'free') ===== */
let currentTier = localStorage.getItem('shuxue-tier') || 'free';
let usageTracking = {
  questionsViewed: 0,
  analyticsUsed: 0,
  uploadsUsed: 0,
  lastResetDate: new Date().toISOString().slice(0,10)
};

function checkTierLimit(feature) {
  const tier = SUBSCRIPTION_TIERS[currentTier];
  const limit = tier.limits[feature];
  if (limit === false) return { allowed: false, reason: '此功能需升级至 PRO' };
  if (limit === true) return { allowed: true };
  if (limit === Infinity) return { allowed: true };
  // Check daily/monthly usage
  if (feature === 'questionsPerDay') {
    return { allowed: usageTracking.questionsViewed < limit, remaining: limit - usageTracking.questionsViewed, limit };
  }
  if (feature === 'analyticsPerMonth') {
    return { allowed: usageTracking.analyticsUsed < limit, remaining: limit - usageTracking.analyticsUsed, limit };
  }
  if (feature === 'uploadsPerDay') {
    return { allowed: usageTracking.uploadsUsed < limit, remaining: limit - usageTracking.uploadsUsed, limit };
  }
  return { allowed: true };
}

function trackUsage(feature) {
  if (feature === 'questionView') usageTracking.questionsViewed++;
  if (feature === 'analytics') usageTracking.analyticsUsed++;
  if (feature === 'upload') usageTracking.uploadsUsed++;
  localStorage.setItem('shuxue-usage', JSON.stringify(usageTracking));
}

function switchTier(tier) {
  currentTier = tier;
  localStorage.setItem('shuxue-tier', tier);
  updateTierBadge();
  updateFeatureLocks();
}

function updateTierBadge() {
  const badge = document.getElementById('tier-badge');
  if (badge) {
    badge.textContent = SUBSCRIPTION_TIERS[currentTier].name;
    badge.className = 'tier-badge ' + currentTier;
  }
}

function updateFeatureLocks() {
  const tier = SUBSCRIPTION_TIERS[currentTier];
  // Unlock/lock features based on tier
  document.querySelectorAll('[data-tier-lock]').forEach(el => {
    const requiredTier = el.dataset.tierLock;
    const tierOrder = ['free', 'pro', 'team', 'api'];
    const currentIdx = tierOrder.indexOf(currentTier);
    const requiredIdx = tierOrder.indexOf(requiredTier);
    if (currentIdx >= requiredIdx) {
      el.classList.remove('feature-lock');
      el.style.opacity = '';
      el.style.cursor = '';
    } else {
      el.classList.add('feature-lock');
      el.style.opacity = '.5';
      el.style.cursor = 'not-allowed';
    }
  });
}

