"""冻结的旧知识目录迁移映射。

该文件只用于首次迁移和空数据库引导。上线后的知识树以数据库为唯一事实源，
新增、移动和改名都必须通过知识图谱 API 完成，不再修改这里的目录。
"""

import uuid


KNOWLEDGE_ID_URL_PREFIX = "https://shuxue.icu/knowledge/"
NODE_TYPES = ("domain", "module", "topic", "concept")

# depth|code|title|difficulty|exam_frequency|expanded
LEGACY_CATALOG = """\
0|FUNC|函数与导数|||1
1|FUNC-01|集合与常用逻辑用语|||0
2|FUNC-01-01|集合的概念与运算|1,2|high|0
2|FUNC-01-02|充分条件与必要条件|2,3|medium|0
1|FUNC-02|函数的概念与基本初等函数|||0
2|FUNC-02-01|函数的概念与表示|1,3|high|0
2|FUNC-02-02|函数的基本性质|2,4|high|0
3|FUNC-02-02-01|单调性|2,4|high|0
3|FUNC-02-02-02|奇偶性|2,4|high|0
3|FUNC-02-02-03|周期性|3,4|medium|0
3|FUNC-02-02-04|对称性|3,5|medium|0
2|FUNC-02-03|幂函数、指数函数、对数函数|2,4|high|0
2|FUNC-02-04|函数的图象|2,4|high|0
2|FUNC-02-05|函数与方程|3,4|medium|0
2|FUNC-02-06|函数模型及其应用|2,3|low|0
1|FUNC-03|三角函数与解三角形|||0
2|FUNC-03-01|任意角和弧度制|1,2|medium|0
2|FUNC-03-02|三角函数的定义|1,3|high|0
2|FUNC-03-03|三角函数的图象与性质|3,4|high|0
2|FUNC-03-04|三角恒等变换|3,4|high|0
2|FUNC-03-05|解三角形|3,4|high|0
1|FUNC-04|数列|||0
2|FUNC-04-01|数列的概念|1,2|medium|0
2|FUNC-04-02|等差数列|2,4|high|0
2|FUNC-04-03|等比数列|2,4|high|0
2|FUNC-04-04|数列求和|3,5|high|0
1|FUNC-05|导数及其应用|||0
2|FUNC-05-01|导数的概念与运算|2,3|high|0
2|FUNC-05-02|导数与函数的单调性|3,4|high|0
2|FUNC-05-03|导数与函数的极值、最值|3,5|high|0
2|FUNC-05-04|导数的综合应用|4,5|high|0
0|GEOM|几何与向量|||0
1|GEOM-01|平面向量|||0
2|GEOM-01-01|向量的概念与线性运算|1,3|high|0
2|GEOM-01-02|向量的数量积|2,4|high|0
2|GEOM-01-03|向量的应用|3,4|medium|0
1|GEOM-02|立体几何|||0
2|GEOM-02-01|空间几何体|2,3|medium|0
2|GEOM-02-02|空间点线面位置关系|3,4|high|0
2|GEOM-02-03|空间向量及其运算|3,4|high|0
2|GEOM-02-04|空间向量在立体几何中的应用|3,5|high|0
1|GEOM-03|解析几何|||0
2|GEOM-03-01|直线与方程|1,3|high|0
2|GEOM-03-02|圆与方程|2,4|high|0
2|GEOM-03-03|椭圆|3,5|high|0
2|GEOM-03-04|双曲线|3,5|high|0
2|GEOM-03-05|抛物线|3,5|high|0
2|GEOM-03-06|直线与圆锥曲线的位置关系|4,5|high|0
0|ALGE|代数与不等式|||0
1|ALGE-01|不等式|||0
2|ALGE-01-01|不等式的性质与解法|1,3|high|0
2|ALGE-01-02|基本不等式|2,4|high|0
2|ALGE-01-03|线性规划|2,3|medium|0
1|ALGE-02|复数|||0
2|ALGE-02-01|复数的概念与运算|1,2|high|0
1|ALGE-03|计数原理与二项式定理|||0
2|ALGE-03-01|排列与组合|3,4|high|0
2|ALGE-03-02|二项式定理|2,4|high|0
0|PROB|概率与统计|||0
1|PROB-01|概率|||0
2|PROB-01-01|古典概型与几何概型|2,3|high|0
2|PROB-01-02|条件概率与独立性|3,4|high|0
2|PROB-01-03|离散型随机变量及其分布|3,5|high|0
2|PROB-01-04|正态分布|2,3|medium|0
1|PROB-02|统计|||0
2|PROB-02-01|抽样方法与数据特征|1,3|high|0
2|PROB-02-02|回归分析与独立性检验|2,4|medium|0
0|CALC|微积分初步|||0
1|CALC-01|微积分基础|||0
2|CALC-01-01|定积分的概念|2,3|low|0
2|CALC-01-02|微积分基本定理|2,4|low|0
"""


def knowledge_node_id(code):
    """由旧代码稳定生成永久内部 ID；同一代码在所有环境中结果一致。"""
    value = uuid.uuid5(uuid.NAMESPACE_URL, f"{KNOWLEDGE_ID_URL_PREFIX}{code}")
    return f"kn_{value.hex}"


def legacy_catalog_nodes():
    """把冻结目录展开为包含父 ID 与同级顺序的迁移记录。"""
    parents = {}
    sibling_counts = {}
    rows = []
    for raw_line in LEGACY_CATALOG.splitlines():
        depth_text, code, title, difficulty_text, frequency, expanded_text = raw_line.split("|")
        depth = int(depth_text)
        parent_code = parents.get(depth - 1) if depth else None
        parent_id = knowledge_node_id(parent_code) if parent_code else None
        sort_order = sibling_counts.get(parent_code, 0)
        sibling_counts[parent_code] = sort_order + 1
        difficulty = [int(value) for value in difficulty_text.split(",")] if difficulty_text else None
        row = {
            "id": knowledge_node_id(code),
            "code": code,
            "parent_id": parent_id,
            "node_type": NODE_TYPES[min(depth, len(NODE_TYPES) - 1)],
            "knowledge_type": "concept",
            "title": title,
            "sort_order": sort_order,
            "status": "published",
            "redirect_to_id": None,
            "metadata": {
                "level": depth + 1,
                "difficulty": difficulty,
                "examFrequency": frequency or None,
                "expanded": expanded_text == "1",
            },
            "version": 1,
        }
        rows.append(row)
        parents[depth] = code
        for stale_depth in [value for value in parents if value > depth]:
            parents.pop(stale_depth)
    return rows
