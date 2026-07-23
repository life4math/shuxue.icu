// 末级知识点正文。math 为 KaTeX 源码，不包含 $ 定界符。
// 每个末级知识点必须有独立条目；页面启动时会校验是否遗漏。
const knowledgeDetails = {
  "FUNC-01-01": { title: "集合的概念与运算", sections: [
    { title: "定义与表示", items: [{ math: "a\\in A,\\quad a\\notin A" }, { text: "常用表示方法：列举法、描述法、Venn 图法" }] },
    { title: "常用数集", items: [{ math: "\\mathbb N,\\ \\mathbb N^*,\\ \\mathbb Z,\\ \\mathbb Q,\\ \\mathbb R,\\ \\mathbb C" }] },
    { title: "集合关系", items: [{ math: "A\\subseteq B" }, { math: "A\\subsetneqq B" }, { text: "含 n 个元素的集合有", suffixMath: "2^n\\text{ 个子集，}2^n-1\\text{ 个真子集}" }] },
    { title: "集合运算", items: [{ math: "A\\cap B,\\quad A\\cup B,\\quad \\complement_U A" }, { math: "\\complement_U(A\\cap B)=\\complement_UA\\cup\\complement_UB" }, { math: "\\complement_U(A\\cup B)=\\complement_UA\\cap\\complement_UB" }] }
  ] },
  "FUNC-01-02": { title: "充分条件与必要条件", sections: [
    { title: "命题关系", items: [{ math: "p\\Rightarrow q", text: "p 是 q 的充分条件，q 是 p 的必要条件" }, { math: "p\\Leftrightarrow q", text: "p、q 互为充分必要条件" }] },
    { title: "四种命题", items: [{ text: "原命题与逆否命题等价，逆命题与否命题等价" }, { math: "\\neg(p\\Rightarrow q)\\Leftrightarrow p\\land\\neg q" }] },
    { title: "量词否定", items: [{ math: "\\neg(\\forall x,\\ p(x))\\Leftrightarrow\\exists x,\\ \\neg p(x)" }, { math: "\\neg(\\exists x,\\ p(x))\\Leftrightarrow\\forall x,\\ \\neg p(x)" }] }
  ] },
  "FUNC-02-01": { title: "函数的概念与表示", sections: [
    { title: "函数三要素", items: [{ text: "定义域、对应关系、值域共同确定一个函数" }, { math: "f:A\\to B,\\quad x\\mapsto f(x)" }] },
    { title: "定义域和值域", items: [{ text: "分母不为零；偶次根式被开方数非负；对数真数为正" }, { math: "\\operatorname{Dom}(f),\\quad \\operatorname{Ran}(f)=\\{f(x)\\mid x\\in A\\}" }] },
    { title: "表示方法", items: [{ text: "解析法、列表法、图象法；分段函数须分区间求值" }] }
  ] },
  "FUNC-02-02-01": { title: "单调性", sections: [
    { title: "定义", items: [{ math: "x_1<x_2\\Rightarrow f(x_1)<f(x_2)", text: "单调递增" }, { math: "x_1<x_2\\Rightarrow f(x_1)>f(x_2)", text: "单调递减" }] },
    { title: "导数判定", items: [{ math: "f'(x)>0\\Rightarrow f(x)\\text{递增}" }, { math: "f'(x)<0\\Rightarrow f(x)\\text{递减}" }] },
    { title: "复合函数", items: [{ text: "同增异减：内外层单调性相同则递增，不同则递减" }] }
  ] },
  "FUNC-02-02-02": { title: "奇偶性", sections: [
    { title: "定义", items: [{ math: "f(-x)=f(x)", text: "偶函数，图象关于 y 轴对称" }, { math: "f(-x)=-f(x)", text: "奇函数，图象关于原点对称" }] },
    { title: "必要条件", items: [{ text: "定义域必须关于原点对称" }, { math: "0\\in D\\text{ 且 }f\\text{ 为奇函数}\\Rightarrow f(0)=0" }] },
    { title: "运算规律", items: [{ text: "奇×奇、偶×偶为偶；奇×偶为奇" }] }
  ] },
  "FUNC-02-02-03": { title: "周期性", sections: [
    { title: "定义", items: [{ math: "f(x+T)=f(x)\\quad(T\\ne0)" }, { text: "满足条件的最小正数 T 称为最小正周期" }] },
    { title: "常用结论", items: [{ math: "f(x+a)=f(x+b)\\Rightarrow T=|a-b|" }, { math: "f(x+a)=-f(x)\\Rightarrow T=2|a|" }] },
    { title: "基本周期", items: [{ math: "T_{\\sin(\\omega x+\\varphi)}=\\frac{2\\pi}{|\\omega|}" }, { math: "T_{\\tan(\\omega x+\\varphi)}=\\frac{\\pi}{|\\omega|}" }] }
  ] },
  "FUNC-02-02-04": { title: "对称性", sections: [
    { title: "轴对称", items: [{ math: "f(a+x)=f(a-x)", text: "图象关于直线", suffixMath: "x=a\\text{ 对称}" }] },
    { title: "中心对称", items: [{ math: "f(a+x)+f(a-x)=2b", text: "图象关于点", suffixMath: "(a,b)\\text{ 对称}" }] },
    { title: "对称与周期", items: [{ text: "两条对称轴间距的 2 倍是周期；两个对称中心间距的 2 倍是周期" }] }
  ] },
  "FUNC-02-03": { title: "幂函数、指数函数、对数函数", sections: [
    { title: "指数与对数", items: [{ math: "a^x=N\\Leftrightarrow \\log_aN=x\\quad(a>0,a\\ne1)" }, { math: "\\log_aMN=\\log_aM+\\log_aN" }, { math: "\\log_ab=\\frac{\\log_cb}{\\log_ca}" }] },
    { title: "单调性", items: [{ math: "a>1:\\ a^x,\\log_ax\\text{递增}" }, { math: "0<a<1:\\ a^x,\\log_ax\\text{递减}" }] },
    { title: "幂函数", items: [{ math: "y=x^\\alpha" }, { text: "性质由指数 α 和定义域共同决定，比较大小时优先利用单调性" }] }
  ] },
  "FUNC-02-04": { title: "函数的图象", sections: [
    { title: "平移", items: [{ math: "y=f(x-a)+b", text: "由", suffixMath: "y=f(x)\\text{ 向右平移 }a\\text{、向上平移 }b" }] },
    { title: "伸缩与翻折", items: [{ math: "y=Af(\\omega x)" }, { math: "y=|f(x)|" }, { math: "y=f(|x|)" }] },
    { title: "识图要点", items: [{ text: "依次检查定义域、零点、单调区间、奇偶性、周期、渐近线与端点" }] }
  ] },
  "FUNC-02-05": { title: "函数与方程", sections: [
    { title: "零点", items: [{ math: "f(x_0)=0\\Leftrightarrow x_0\\text{ 是方程 }f(x)=0\\text{ 的根}" }] },
    { title: "零点存在性", items: [{ math: "f(a)f(b)<0", text: "且 f 在 [a,b] 连续，则 (a,b) 内至少有一个零点" }] },
    { title: "根的个数", items: [{ text: "转化为两函数图象交点个数，结合单调性、极值和参数分类讨论" }] }
  ] },
  "FUNC-02-06": { title: "函数模型及其应用", sections: [
    { title: "常见模型", items: [{ math: "y=kx+b" }, { math: "y=ax^2+bx+c" }, { math: "y=ab^x" }, { math: "y=a\\ln x+b" }] },
    { title: "建模流程", items: [{ text: "明确变量与单位—建立关系—确定定义域—求解—检验实际意义" }] },
    { title: "增长比较", items: [{ text: "长期增长速度通常为：指数函数快于幂函数，幂函数快于对数函数" }] }
  ] },
  "FUNC-03-01": { title: "任意角和弧度制", sections: [
    { title: "角的推广", items: [{ math: "\\alpha+2k\\pi\\quad(k\\in\\mathbb Z)", text: "表示与 α 终边相同的角" }] },
    { title: "弧度制", items: [{ math: "180^\\circ=\\pi\\ \\mathrm{rad}" }, { math: "l=|\\alpha|r" }, { math: "S=\\frac12|\\alpha|r^2=\\frac12lr" }] },
    { title: "象限判断", items: [{ text: "先化到 [0,2π) 内，再依据终边位置判断象限" }] }
  ] },
  "FUNC-03-02": { title: "三角函数的定义", sections: [
    { title: "任意角定义", items: [{ math: "\\sin\\alpha=\\frac yr,\\quad\\cos\\alpha=\\frac xr,\\quad\\tan\\alpha=\\frac yx" }] },
    { title: "基本关系", items: [{ math: "\\sin^2\\alpha+\\cos^2\\alpha=1" }, { math: "\\tan\\alpha=\\frac{\\sin\\alpha}{\\cos\\alpha}" }] },
    { title: "诱导公式", items: [{ text: "奇变偶不变，符号看象限" }] }
  ] },
  "FUNC-03-03": { title: "三角函数的图象与性质", sections: [
    { title: "正弦型函数", items: [{ math: "y=A\\sin(\\omega x+\\varphi)+b" }, { math: "T=\\frac{2\\pi}{|\\omega|},\\quad y_{\\max}=b+|A|,\\quad y_{\\min}=b-|A|" }] },
    { title: "五点作图", items: [{ math: "0,\\ \\frac\\pi2,\\ \\pi,\\ \\frac{3\\pi}2,\\ 2\\pi", text: "令整体相位依次取五个关键值" }] },
    { title: "性质", items: [{ text: "由整体角的范围求单调区间、对称轴和对称中心" }] }
  ] },
  "FUNC-03-04": { title: "三角恒等变换", sections: [
    { title: "和差公式", items: [{ math: "\\sin(\\alpha\\pm\\beta)=\\sin\\alpha\\cos\\beta\\pm\\cos\\alpha\\sin\\beta" }, { math: "\\cos(\\alpha\\pm\\beta)=\\cos\\alpha\\cos\\beta\\mp\\sin\\alpha\\sin\\beta" }] },
    { title: "倍角公式", items: [{ math: "\\sin2\\alpha=2\\sin\\alpha\\cos\\alpha" }, { math: "\\cos2\\alpha=2\\cos^2\\alpha-1=1-2\\sin^2\\alpha" }] },
    { title: "辅助角", items: [{ math: "a\\sin x+b\\cos x=\\sqrt{a^2+b^2}\\sin(x+\\varphi)" }] }
  ] },
  "FUNC-03-05": { title: "解三角形", sections: [
    { title: "正弦定理", items: [{ math: "\\frac a{\\sin A}=\\frac b{\\sin B}=\\frac c{\\sin C}=2R" }] },
    { title: "余弦定理", items: [{ math: "a^2=b^2+c^2-2bc\\cos A" }] },
    { title: "面积公式", items: [{ math: "S=\\frac12bc\\sin A=\\frac{abc}{4R}=\\sqrt{p(p-a)(p-b)(p-c)}" }] }
  ] },
  "FUNC-04-01": { title: "数列的概念", sections: [
    { title: "基本概念", items: [{ math: "\\{a_n\\}:a_1,a_2,\\ldots,a_n,\\ldots" }, { text: "数列可视为定义域为正整数集或其有限子集的函数" }] },
    { title: "通项与递推", items: [{ math: "a_n=f(n)" }, { math: "a_{n+1}=F(a_n)" }] },
    { title: "前 n 项和", items: [{ math: "S_n=\\sum_{k=1}^n a_k,\\quad a_n=S_n-S_{n-1}\\ (n\\ge2)" }] }
  ] },
  "FUNC-04-02": { title: "等差数列", sections: [
    { title: "定义与通项", items: [{ math: "a_{n+1}-a_n=d" }, { math: "a_n=a_1+(n-1)d" }] },
    { title: "求和", items: [{ math: "S_n=\\frac{n(a_1+a_n)}2=na_1+\\frac{n(n-1)}2d" }] },
    { title: "性质", items: [{ math: "m+n=p+q\\Rightarrow a_m+a_n=a_p+a_q" }, { math: "a_n=A n+B" }] }
  ] },
  "FUNC-04-03": { title: "等比数列", sections: [
    { title: "定义与通项", items: [{ math: "\\frac{a_{n+1}}{a_n}=q\\quad(a_n\\ne0)" }, { math: "a_n=a_1q^{n-1}" }] },
    { title: "求和", items: [{ math: "q\\ne1:\\ S_n=\\frac{a_1(1-q^n)}{1-q}" }, { math: "q=1:\\ S_n=na_1" }] },
    { title: "性质", items: [{ math: "m+n=p+q\\Rightarrow a_ma_n=a_pa_q" }] }
  ] },
  "FUNC-04-04": { title: "数列求和", sections: [
    { title: "常用方法", items: [{ text: "公式法、分组求和、错位相减、裂项相消、倒序相加" }] },
    { title: "裂项示例", items: [{ math: "\\frac1{n(n+1)}=\\frac1n-\\frac1{n+1}" }] },
    { title: "错位相减", items: [{ text: "适用于“等差×等比”型数列，比较 Sₙ 与 qSₙ 后相减" }] }
  ] },
  "FUNC-05-01": { title: "导数的概念与运算", sections: [
    { title: "定义", items: [{ math: "f'(x_0)=\\lim_{\\Delta x\\to0}\\frac{f(x_0+\\Delta x)-f(x_0)}{\\Delta x}" }] },
    { title: "几何意义", items: [{ math: "k_{\\text{切线}}=f'(x_0)" }, { math: "y-f(x_0)=f'(x_0)(x-x_0)" }] },
    { title: "运算法则", items: [{ math: "(uv)'=u'v+uv'" }, { math: "\\left(\\frac uv\\right)'=\\frac{u'v-uv'}{v^2}" }, { math: "[f(g(x))]'=f'(g(x))g'(x)" }] }
  ] },
  "FUNC-05-02": { title: "导数与函数的单调性", sections: [
    { title: "判定", items: [{ math: "f'(x)>0\\Rightarrow f\\text{递增},\\quad f'(x)<0\\Rightarrow f\\text{递减}" }] },
    { title: "步骤", items: [{ text: "求定义域—求导—解 f′(x)>0 与 f′(x)<0—写出单调区间" }] },
    { title: "参数问题", items: [{ text: "将恒单调转化为导函数在定义域上恒非负或恒非正，并检查等号点" }] }
  ] },
  "FUNC-05-03": { title: "导数与函数的极值、最值", sections: [
    { title: "极值", items: [{ text: "f′ 在驻点左正右负为极大值，左负右正为极小值" }, { math: "f'(x_0)=0", text: "只是可导函数取得极值的必要非充分条件" }] },
    { title: "闭区间最值", items: [{ text: "比较区间内所有极值点与两个端点的函数值" }] },
    { title: "参数分离", items: [{ math: "f(x,a)\\ge0\\Longleftrightarrow a\\ge g(x)", text: "再求 g(x) 的最值" }] }
  ] },
  "FUNC-05-04": { title: "导数的综合应用", sections: [
    { title: "恒成立与存在性", items: [{ math: "\\forall x,\\ f(x,a)\\ge0\\Longleftrightarrow \\min_x f(x,a)\\ge0" }, { math: "\\exists x,\\ f(x,a)>0\\Longleftrightarrow \\max_x f(x,a)>0" }] },
    { title: "不等式证明", items: [{ text: "移项构造函数，通过单调性或最值证明函数符号" }, { math: "e^x\\ge x+1,\\quad \\ln x\\le x-1" }] },
    { title: "零点与切线", items: [{ text: "利用单调区间控制零点个数；临界参数常对应相切，即方程与导数方程联立" }] }
  ] },
  "GEOM-01-01": { title: "向量的概念与线性运算", sections: [
    { title: "基本概念", items: [{ text: "向量同时具有大小和方向；零向量方向任意；单位向量模为 1" }, { math: "|\\vec a|=\\sqrt{x^2+y^2}" }] },
    { title: "线性运算", items: [{ math: "\\vec a+\\vec b=(x_1+x_2,y_1+y_2)" }, { math: "\\lambda\\vec a=(\\lambda x_1,\\lambda y_1)" }] },
    { title: "共线条件", items: [{ math: "\\vec a\\parallel\\vec b\\Leftrightarrow x_1y_2-x_2y_1=0" }] }
  ] },
  "GEOM-01-02": { title: "向量的数量积", sections: [
    { title: "定义与坐标", items: [{ math: "\\vec a\\cdot\\vec b=|\\vec a||\\vec b|\\cos\\theta" }, { math: "\\vec a\\cdot\\vec b=x_1x_2+y_1y_2" }] },
    { title: "垂直与夹角", items: [{ math: "\\vec a\\perp\\vec b\\Leftrightarrow\\vec a\\cdot\\vec b=0" }, { math: "\\cos\\theta=\\frac{\\vec a\\cdot\\vec b}{|\\vec a||\\vec b|}" }] },
    { title: "性质", items: [{ math: "|\\vec a\\cdot\\vec b|\\le|\\vec a||\\vec b|" }] }
  ] },
  "GEOM-01-03": { title: "向量的应用", sections: [
    { title: "几何证明", items: [{ text: "平行转化为向量共线，垂直转化为数量积为零" }] },
    { title: "长度与夹角", items: [{ math: "|\\vec a\\pm\\vec b|^2=|\\vec a|^2+|\\vec b|^2\\pm2\\vec a\\cdot\\vec b" }] },
    { title: "三角形四心", items: [{ text: "利用位置向量、数量积与线性组合刻画重心、垂心、外心、内心" }] }
  ] },
  "GEOM-02-01": { title: "空间几何体", sections: [
    { title: "表面积与体积", items: [{ math: "V_{\\text{柱}}=Sh,\\quad V_{\\text{锥}}=\\frac13Sh" }, { math: "V_{\\text{球}}=\\frac43\\pi R^3,\\quad S_{\\text{球}}=4\\pi R^2" }] },
    { title: "三视图与直观图", items: [{ text: "长对正、高平齐、宽相等；被遮挡轮廓用虚线表示" }] },
    { title: "截面", items: [{ text: "截面与每个面的交线均为线段，依次寻找公共点并连接" }] }
  ] },
  "GEOM-02-02": { title: "空间点线面位置关系", sections: [
    { title: "平行判定", items: [{ text: "线面平行：平面外直线平行于平面内一条直线" }, { text: "面面平行：一个平面内两条相交直线分别平行于另一平面" }] },
    { title: "垂直判定", items: [{ text: "线面垂直：直线垂直于平面内两条相交直线" }, { text: "面面垂直：一个平面经过另一个平面的垂线" }] },
    { title: "角与距离", items: [{ math: "\\sin\\theta=|\\vec l\\cdot\\vec n|/(|\\vec l||\\vec n|)", text: "线面角" }] }
  ] },
  "GEOM-02-03": { title: "空间向量及其运算", sections: [
    { title: "坐标运算", items: [{ math: "\\vec a=(x_1,y_1,z_1),\\quad |\\vec a|=\\sqrt{x_1^2+y_1^2+z_1^2}" }, { math: "\\vec a\\cdot\\vec b=x_1x_2+y_1y_2+z_1z_2" }] },
    { title: "共线与共面", items: [{ math: "\\vec a=\\lambda\\vec b", text: "向量共线" }, { math: "\\vec p=x\\vec a+y\\vec b", text: "向量共面" }] },
    { title: "法向量", items: [{ math: "\\vec n\\cdot\\vec a=\\vec n\\cdot\\vec b=0", text: "其中 a、b 是平面内不共线向量" }] }
  ] },
  "GEOM-02-04": { title: "空间向量在立体几何中的应用", sections: [
    { title: "空间角", items: [{ math: "\\cos\\theta=\\frac{|\\vec a\\cdot\\vec b|}{|\\vec a||\\vec b|}", text: "异面直线夹角" }, { math: "\\cos\\theta=\\frac{|\\vec n_1\\cdot\\vec n_2|}{|\\vec n_1||\\vec n_2|}", text: "二面角需结合图形判断正负" }] },
    { title: "距离", items: [{ math: "d=\\frac{|\\overrightarrow{AP}\\cdot\\vec n|}{|\\vec n|}", text: "点 P 到平面的距离" }] },
    { title: "建系原则", items: [{ text: "优先选择两两垂直且交于一点的直线作为坐标轴" }] }
  ] },
  "GEOM-03-01": { title: "直线与方程", sections: [
    { title: "直线方程", items: [{ math: "y-y_0=k(x-x_0)" }, { math: "Ax+By+C=0" }, { math: "\\frac xa+\\frac yb=1" }] },
    { title: "位置关系", items: [{ math: "k_1=k_2", text: "平行（截距不同）" }, { math: "k_1k_2=-1", text: "垂直" }] },
    { title: "距离", items: [{ math: "d=\\frac{|Ax_0+By_0+C|}{\\sqrt{A^2+B^2}}" }] }
  ] },
  "GEOM-03-02": { title: "圆与方程", sections: [
    { title: "标准方程", items: [{ math: "(x-a)^2+(y-b)^2=r^2" }, { text: "圆心", suffixMath: "(a,b)" }, { text: "半径", suffixMath: "r" }] },
    { title: "直线与圆", items: [{ math: "d<r,\\ d=r,\\ d>r", text: "分别对应相交、相切、相离" }, { math: "|AB|=2\\sqrt{r^2-d^2}" }] },
    { title: "两圆关系", items: [{ text: "比较圆心距 d 与", suffixMath: "r_1+r_2,\\ |r_1-r_2|" }] }
  ] },
  "GEOM-03-03": { title: "椭圆", sections: [
    { title: "定义与方程", items: [{ math: "|PF_1|+|PF_2|=2a" }, { math: "\\frac{x^2}{a^2}+\\frac{y^2}{b^2}=1\\quad(a>b>0)" }] },
    { title: "基本关系", items: [{ math: "a^2=b^2+c^2,\\quad e=\\frac ca" }, { text: "长轴长 2a，短轴长 2b，焦距 2c" }] },
    { title: "焦半径", items: [{ math: "PF_1=a+ex,\\quad PF_2=a-ex", text: "焦点在 x 轴时" }] }
  ] },
  "GEOM-03-04": { title: "双曲线", sections: [
    { title: "定义与方程", items: [{ math: "\\bigl||PF_1|-|PF_2|\\bigr|=2a" }, { math: "\\frac{x^2}{a^2}-\\frac{y^2}{b^2}=1" }] },
    { title: "基本关系", items: [{ math: "c^2=a^2+b^2,\\quad e=\\frac ca>1" }] },
    { title: "渐近线", items: [{ math: "y=\\pm\\frac ba x", text: "焦点在 x 轴的双曲线" }] }
  ] },
  "GEOM-03-05": { title: "抛物线", sections: [
    { title: "定义", items: [{ text: "到定点 F 与到定直线 l 距离相等的点的轨迹" }] },
    { title: "标准方程", items: [{ math: "y^2=2px\\quad(p>0)" }, { text: "焦点", suffixMath: "F(\\frac p2,0)" }, { text: "准线", suffixMath: "x=-\\frac p2" }] },
    { title: "焦半径", items: [{ math: "|PF|=x_0+\\frac p2", text: "点", suffixMath: "P(x_0,y_0)\\text{ 在 }y^2=2px\\text{ 上}" }] }
  ] },
  "GEOM-03-06": { title: "直线与圆锥曲线的位置关系", sections: [
    { title: "联立与判别式", items: [{ math: "\\Delta>0,\\ \\Delta=0,\\ \\Delta<0", text: "分别对应两个交点、相切、无交点" }] },
    { title: "韦达定理", items: [{ math: "x_1+x_2=-\\frac BA,\\quad x_1x_2=\\frac CA" }, { math: "|AB|=\\sqrt{1+k^2}|x_1-x_2|" }] },
    { title: "常见问题", items: [{ text: "定点、定值、弦中点、面积最值、斜率关系；注意直线斜率不存在的情形" }] }
  ] },
  "ALGE-01-01": { title: "不等式的性质与解法", sections: [
    { title: "基本性质", items: [{ math: "a>b\\Rightarrow a+c>b+c" }, { math: "a>b,\\ c>0\\Rightarrow ac>bc" }, { math: "a>b,\\ c<0\\Rightarrow ac<bc" }] },
    { title: "一元二次不等式", items: [{ text: "结合二次函数开口、零点和判别式确定解集" }, { math: "ax^2+bx+c=a(x-x_1)(x-x_2)" }] },
    { title: "分式与绝对值", items: [{ text: "分式不等式移项通分后用穿针引线；绝对值按零点分区间讨论" }] }
  ] },
  "ALGE-01-02": { title: "基本不等式", sections: [
    { title: "核心公式", items: [{ math: "a^2+b^2\\ge2ab" }, { math: "\\frac{a+b}{2}\\ge\\sqrt{ab}\\quad(a,b>0)" }] },
    { title: "取等条件", items: [{ math: "a=b", text: "使用基本不等式必须同时满足正、定、等" }] },
    { title: "常用变形", items: [{ math: "x+\\frac ax\\ge2\\sqrt a\\quad(x>0,a>0)" }, { math: "(a+b)^2\\le2(a^2+b^2)" }] }
  ] },
  "ALGE-01-03": { title: "线性规划", sections: [
    { title: "可行域", items: [{ text: "将二元一次不等式组表示为平面上的公共区域" }] },
    { title: "目标函数", items: [{ math: "z=ax+by\\Rightarrow y=-\\frac abx+\\frac zb" }, { text: "平移目标直线，在边界顶点处取得最值" }] },
    { title: "非线性目标", items: [{ math: "\\frac{y-b}{x-a}", text: "可理解为斜率" }, { math: "(x-a)^2+(y-b)^2", text: "可理解为距离平方" }] }
  ] },
  "ALGE-02-01": { title: "复数的概念与运算", sections: [
    { title: "代数形式", items: [{ math: "z=a+bi\\quad(a,b\\in\\mathbb R,\\ i^2=-1)" }, { math: "\\overline z=a-bi,\\quad |z|=\\sqrt{a^2+b^2}" }] },
    { title: "四则运算", items: [{ math: "(a+bi)(c+di)=(ac-bd)+(ad+bc)i" }, { math: "\\frac{z_1}{z_2}=\\frac{z_1\\overline{z_2}}{|z_2|^2}" }] },
    { title: "几何意义", items: [{ text: "复数 z 对应复平面上的点 (a,b) 和向量；|z₁-z₂| 表示两点距离" }] }
  ] },
  "ALGE-03-01": { title: "排列与组合", sections: [
    { title: "计数原理", items: [{ text: "分类完成用加法原理，分步完成用乘法原理" }] },
    { title: "排列组合", items: [{ math: "A_n^m=\\frac{n!}{(n-m)!}" }, { math: "C_n^m=\\frac{n!}{m!(n-m)!}=C_n^{n-m}" }] },
    { title: "常用策略", items: [{ text: "特殊元素优先、相邻捆绑、不相邻插空、至少问题用间接法" }] }
  ] },
  "ALGE-03-02": { title: "二项式定理", sections: [
    { title: "展开式", items: [{ math: "(a+b)^n=\\sum_{k=0}^n C_n^k a^{n-k}b^k" }] },
    { title: "通项", items: [{ math: "T_{k+1}=C_n^k a^{n-k}b^k" }] },
    { title: "系数性质", items: [{ math: "\\sum_{k=0}^nC_n^k=2^n" }, { math: "\\sum_{k=0}^n(-1)^kC_n^k=0" }, { text: "最大项位于展开式中部附近" }] }
  ] },
  "PROB-01-01": { title: "古典概型与几何概型", sections: [
    { title: "古典概型", items: [{ math: "P(A)=\\frac{m}{n}", text: "基本事件有限且等可能" }] },
    { title: "几何概型", items: [{ math: "P(A)=\\frac{\\mu(A)}{\\mu(\\Omega)}", text: "μ 可表示长度、面积或体积" }] },
    { title: "基本性质", items: [{ math: "P(\\overline A)=1-P(A)" }, { math: "P(A\\cup B)=P(A)+P(B)-P(A\\cap B)" }] }
  ] },
  "PROB-01-02": { title: "条件概率与独立性", sections: [
    { title: "条件概率", items: [{ math: "P(B\\mid A)=\\frac{P(AB)}{P(A)}\\quad(P(A)>0)" }, { math: "P(AB)=P(A)P(B\\mid A)" }] },
    { title: "相互独立", items: [{ math: "P(AB)=P(A)P(B)" }, { text: "独立与互斥是不同概念；非零概率的互斥事件不独立" }] },
    { title: "全概率", items: [{ math: "P(B)=\\sum_iP(A_i)P(B\\mid A_i)" }] }
  ] },
  "PROB-01-03": { title: "离散型随机变量及其分布", sections: [
    { title: "分布列", items: [{ math: "P(X=x_i)=p_i,\\quad p_i\\ge0,\\quad\\sum_i p_i=1" }] },
    { title: "数字特征", items: [{ math: "E(X)=\\sum_i x_ip_i" }, { math: "D(X)=E(X^2)-[E(X)]^2" }] },
    { title: "常见分布", items: [{ math: "X\\sim B(n,p):\\ E(X)=np,\\ D(X)=np(1-p)" }, { text: "超几何分布是不放回抽样，二项分布是独立重复试验" }] }
  ] },
  "PROB-01-04": { title: "正态分布", sections: [
    { title: "模型", items: [{ math: "X\\sim N(\\mu,\\sigma^2)" }, { text: "曲线关于 x=μ 对称，σ 越大曲线越矮宽" }] },
    { title: "三倍标准差", items: [{ math: "P(\\mu-\\sigma<X\\le\\mu+\\sigma)\\approx0.6827" }, { math: "P(|X-\\mu|\\le2\\sigma)\\approx0.9545" }, { math: "P(|X-\\mu|\\le3\\sigma)\\approx0.9973" }] },
    { title: "标准化", items: [{ math: "Z=\\frac{X-\\mu}{\\sigma}\\sim N(0,1)" }] }
  ] },
  "PROB-02-01": { title: "抽样方法与数据特征", sections: [
    { title: "抽样", items: [{ text: "简单随机抽样保证等可能；分层抽样按各层容量比例抽取" }, { math: "\\frac{n_i}{N_i}=\\frac nN" }] },
    { title: "集中趋势", items: [{ text: "平均数、中位数、众数描述数据中心位置" }, { math: "\\bar x=\\frac1n\\sum_{i=1}^n x_i" }] },
    { title: "离散程度", items: [{ math: "s^2=\\frac1n\\sum_{i=1}^n(x_i-\\bar x)^2" }, { text: "极差、方差、标准差越大，数据越分散" }] }
  ] },
  "PROB-02-02": { title: "回归分析与独立性检验", sections: [
    { title: "相关与回归", items: [{ math: "\\hat y=\\hat b x+\\hat a" }, { math: "\\hat b=\\frac{\\sum(x_i-\\bar x)(y_i-\\bar y)}{\\sum(x_i-\\bar x)^2},\\quad \\hat a=\\bar y-\\hat b\\bar x" }] },
    { title: "相关系数", items: [{ math: "-1\\le r\\le1" }, { text: "|r| 越接近 1，线性相关程度越强；相关不代表因果" }] },
    { title: "独立性检验", items: [{ math: "\\chi^2=\\sum\\frac{(O-E)^2}{E}" }, { text: "将统计量与临界值比较，判断两个分类变量是否有关联" }] }
  ] },
  "CALC-01-01": { title: "定积分的概念", sections: [
    { title: "定义思想", items: [{ math: "\\int_a^b f(x)\\,\\mathrm dx=\\lim_{n\\to\\infty}\\sum_{i=1}^n f(\\xi_i)\\Delta x_i" }, { text: "核心是分割、近似、求和、取极限" }] },
    { title: "几何意义", items: [{ text: "定积分表示带符号面积：x 轴上方面积为正，下方面积为负" }] },
    { title: "性质", items: [{ math: "\\int_a^b(f\\pm g)\\,dx=\\int_a^bf\\,dx\\pm\\int_a^bg\\,dx" }, { math: "\\int_a^b f\\,dx=\\int_a^c f\\,dx+\\int_c^b f\\,dx" }] }
  ] },
  "CALC-01-02": { title: "微积分基本定理", sections: [
    { title: "牛顿—莱布尼茨公式", items: [{ math: "\\int_a^b f(x)\\,\\mathrm dx=F(b)-F(a)", text: "其中", suffixMath: "F'(x)=f(x)" }] },
    { title: "常用原函数", items: [{ math: "\\int x^n\\,dx=\\frac{x^{n+1}}{n+1}+C\\quad(n\\ne-1)" }, { math: "\\int e^x\\,dx=e^x+C" }, { math: "\\int\\frac1x\\,dx=\\ln|x|+C" }] },
    { title: "变上限积分", items: [{ math: "\\frac{d}{dx}\\int_a^x f(t)\\,dt=f(x)" }] }
  ] }
};

function validateKnowledgeDetails(tree) {
  const leafIds = [];
  const walk = nodes => nodes.forEach(node => {
    if (node.children && node.children.length) walk(node.children);
    else leafIds.push(node.id);
  });
  walk(tree);
  const missing = leafIds.filter(id => !knowledgeDetails[id]);
  const extra = Object.keys(knowledgeDetails).filter(id => !leafIds.includes(id));
  if (missing.length || extra.length) {
    console.warn("知识点正文校验未通过", { missing, extra });
  }
  return { leafCount: leafIds.length, detailCount: Object.keys(knowledgeDetails).length, missing, extra };
}
