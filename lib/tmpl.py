"""HTML 模板 —— 标记全在 `src/templates/` 下的 `.html` 里，Python 只留计算。

原先每个生成器都在 f-string 里手写 `\\n`、手写缩进空格、手写 `html.escape()`，
460 行带标签的字符串散在 9 个文件里。漏一个 escape 就是一个 XSS 形状的 bug，
缩进算错一格看不出来，改版式得在 Python 里数引号。标记搬进模板文件之后：

    escape      autoescape=True 兜住，模板里不写 escape。**信任的 HTML 才用 |safe**
    缩进        模板里怎么写就怎么出，不用在 Python 里拼空格
    写错变量名  StrictUndefined 当场报错，不是静默出一个空字符串

## 三条要守的

1. **`|safe` 只给自己生成的 HTML。** spec 里人写的文字一律不加 —— 那是输入。
   富文本（`rich()` 那种把 `*字*` 变成 `<em>`）必须**先 escape 再插标签**，
   函数内部保证这一点，出来的才允许 `|safe`。
2. **行内元素之间不许留空白。** `<span>a</span><span>b</span>` 中间换行 + 缩进，
   浏览器会折成一个空格，版式就变了（间距、换行位置全跟着动）。模板里这种地方
   用 `{#- -#}` 或者干脆写在一行。**这是这次重构唯一会改变渲染结果的坑。**
3. **上下文的键不许叫 `items` / `keys` / `values` / `get` / `copy` / `update`。**
   Jinja 的 `a.b` 先找属性再找键，传 dict 进去时 `sec.items` 拿到的是 dict 自带的
   那个方法，渲染出来是 `<built-in method items>` 或者当场 TypeError。
   踩过两次（目录页的 `sections`、打卡单的 `bullets`）。
4. **模板里不做计算。** 分子分母、百分比、类名的选择留在 Python 里 ——
   模板拿到的是算好的值。`{% if %}` 只用来决定「这块出不出」。

## 一处无害的差异

markupsafe 把 `'` 转成 `&#39;`、`"` 转成 `&#34;`，`html.escape` 转成 `&#x27;` / `&quot;`。
同一个字符，渲染一样。搬过来的时候整站只有带撇号的英文单词（can't、wasn't）会
在 diff 里显出来 —— 那不是 bug，别去"修"。

## 目录

    src/templates/page.html          全站页面骨架（head / og / 资产链接 / 页脚）
    src/templates/<栏目>/*.html      各栏目的版式
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import paths

TEMPLATES = paths.SRC / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=True,
    # trim_blocks: {% %} 后面紧跟的那个换行吃掉；lstrip_blocks: {% %} 前面的缩进吃掉。
    # 两个一起开，模板才能按正常缩进写而不在产物里留下一堆空行和游离空格。
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    # 写错变量名要当场炸。默认的 Undefined 会静默渲染成空字符串 ——
    # 那正是「改了半天发现改的是另一个文件」那类问题的来路。
    undefined=StrictUndefined,
)


def render(name: str, **ctx) -> str:
    """渲染 `src/templates/<name>`，关键字参数就是模板上下文。"""
    return env.get_template(name).render(**ctx)


def body(name: str, **ctx) -> str:
    """渲染一段 `<body>` 里的内容 —— 同 `render()`，只是去掉尾部换行。

    page.html 自己在 `{{ body }}` 后面带一个换行，模板文件末尾也有一个，
    不去掉就每页多一个空行（第一次改完就是这么发现的）。
    """
    return render(name, **ctx).rstrip("\n")
