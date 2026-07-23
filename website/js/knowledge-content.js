// 知识点正文。math 为 KaTeX 源码，不包含 $ 定界符。
const knowledgeDetails = {
  "FUNC-01-01": {
    title: "集合",
    sections: [
      { title: "定义", items: [{ math: "a \\in A,\\quad a \\notin A" }] },
      { title: "特殊集合", items: [
        { math: "\\mathbb{N},\\ \\mathbb{N}^{*},\\ \\mathbb{N}_{+}" },
        { math: "\\mathbb{Q},\\ \\mathbb{Z},\\ \\mathbb{R},\\ \\mathbb{C}" }
      ] },
      { title: "集合的关系", items: [
        { math: "A \\subseteq B", text: "包含于，若集合 A 有 n 个元素，则子集个数为", suffixMath: "2^n" },
        { math: "A \\subsetneqq B", text: "真包含于，真子集个数为", suffixMath: "2^n-1" },
        { math: "\\varnothing \\subseteq A,\\quad \\varnothing \\subseteq \\varnothing" }
      ] },
      { title: "集合的运算", items: [
        { math: "A \\cap B=\\{x\\mid x\\in A\\ \\text{且}\\ x\\in B\\}" },
        { math: "A \\cup B=\\{x\\mid x\\in A\\ \\text{或}\\ x\\in B\\}" },
        { math: "\\complement_U A=\\{x\\mid x\\in U\\ \\text{且}\\ x\\notin A\\}" }
      ] },
      { title: "运算性质", items: [
        { math: "\\complement_U(A\\cap B)=\\complement_U A\\cup\\complement_U B" },
        { math: "\\complement_U(A\\cup B)=\\complement_U A\\cap\\complement_U B" },
        { text: "容斥原理" }
      ] }
    ]
  },
  "FUNC-01-02": {
    title: "充分条件与必要条件",
    sections: [
      { title: "命题关系", items: [
        { math: "p\\Rightarrow q", text: "p 是 q 的充分条件，q 是 p 的必要条件" },
        { math: "p\\Leftrightarrow q", text: "p 是 q 的充分必要条件" }
      ] },
      { title: "常用判断", items: [
        { text: "原命题与逆否命题等价" },
        { math: "\\neg(p\\Rightarrow q)\\Leftrightarrow p\\land\\neg q" }
      ] }
    ]
  },
  "FUNC-02-02-01": {
    title: "单调性",
    sections: [
      { title: "定义", items: [
        { math: "x_1<x_2\\Rightarrow f(x_1)<f(x_2)", text: "函数在区间上单调递增" },
        { math: "x_1<x_2\\Rightarrow f(x_1)>f(x_2)", text: "函数在区间上单调递减" }
      ] },
      { title: "导数判定", items: [
        { math: "f'(x)>0", text: "对应区间上单调递增" },
        { math: "f'(x)<0", text: "对应区间上单调递减" }
      ] }
    ]
  },
  "GEOM-01-02": {
    title: "向量的数量积",
    sections: [
      { title: "定义与坐标", items: [
        { math: "\\vec a\\cdot\\vec b=|\\vec a||\\vec b|\\cos\\theta" },
        { math: "\\vec a=(x_1,y_1),\\ \\vec b=(x_2,y_2)\\Rightarrow\\vec a\\cdot\\vec b=x_1x_2+y_1y_2" }
      ] },
      { title: "垂直条件", items: [
        { math: "\\vec a\\perp\\vec b\\Leftrightarrow\\vec a\\cdot\\vec b=0" }
      ] }
    ]
  },
  "PROB-01-01": {
    title: "古典概型与几何概型",
    sections: [
      { title: "古典概型", items: [
        { math: "P(A)=\\frac{m}{n}", text: "m 为事件 A 包含的基本事件数，n 为基本事件总数" }
      ] },
      { title: "几何概型", items: [
        { math: "P(A)=\\frac{\\text{构成事件 }A\\text{ 的区域测度}}{\\text{试验全部结果的区域测度}}" }
      ] }
    ]
  },
  "CALC-01-02": {
    title: "微积分基本定理",
    sections: [
      { title: "牛顿—莱布尼茨公式", items: [
        { math: "\\int_a^b f(x)\\,\\mathrm dx=F(b)-F(a)", text: "其中", suffixMath: "F'(x)=f(x)" }
      ] }
    ]
  }
};
