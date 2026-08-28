"""study 站点的生成器工具集。

lib/ 是三科共用的工具，**不认识任何科目** —— 一个 src/ 下的东西都不 import。
src/ 是认识科目的代码和资产（generator/ 一科一目录、templates/ 一栏目一版式）。
内容一个字都不在这两棵树里，全在 storage/。产物落 dist/，不进 git。

判断一段代码该放哪：换个科目还用得上 → lib/，只有这一科用 → src/generator/<科>/。
"""
