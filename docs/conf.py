import os
import sys
import importlib.metadata

# Ensure the project root and extensions dir are in the path
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("_ext"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "nbsphinx",
    "grid_list",
]

autosummary_generate = True
autosummary_imported_members = False

# Exclude ts_fields module from autosummary stub generation
autosummary_mock_imports = ["esapp.components.ts_fields"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "member-order": "groupwise",
}

# Skip TS class and TSField from autodoc - we use custom tables instead
def autodoc_skip_member(app, what, name, obj, skip, options):
    # Skip the TS class and all its nested classes
    if name in ("TS", "TSField"):
        return True
    # Skip nested TS category classes (Area, Branch, Bus, Gen, etc.)
    if hasattr(obj, "__module__") and "ts_fields" in str(getattr(obj, "__module__", "")):
        return True
    return skip

def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)

autodoc_preserve_defaults = True
todo_include_todos = True
autosectionlabel_prefix_document = True

autoclass_content = "init"
autodoc_typehints = "none"
add_module_names = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
}

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_use_param = False
napoleon_use_rtype = False
napoleon_preprocess_types = True
napoleon_type_aliases = {
    "np": "numpy",
    "np.ndarray": "~numpy.ndarray",
    "pd": "pandas",
    "pd.DataFrame": "~pandas.DataFrame",
    "optional": "typing.Optional",
    "union": "typing.Union",
    "list": "list",
    "dict": "dict",
    "bool": "bool",
    "int": "int",
    "float": "float",
}

exclude_patterns = [
    "_build",
    "**/PWRaw",
]

nbsphinx_execute = 'never'
nbsphinx_allow_errors = True
html_sourcelink_suffix = ''

# nbsphinx styling configuration
nbsphinx_input_prompt = 'In [%s]:'
nbsphinx_output_prompt = 'Out[%s]:'
nbsphinx_prompt_width = '0pt'  # Hide prompt in PDF for cleaner look

# Custom CSS classes for notebook cells (used by nbsphinx)
nbsphinx_prolog = r"""
{% set docname = env.doc2path(env.docname, base=None) %}

.. only:: html

    .. role:: raw-html(raw)
        :format: html

"""
master_doc = "index"

project = "ESA++"
copyright = "2026, Luke Lowery"
author = "Luke Lowery"

try:
    version = importlib.metadata.version("esapp")
except importlib.metadata.PackageNotFoundError:
    version = "unknown"
release = version

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 2,
}
html_static_path = ["_static"]
html_css_files = ["custom.css", "custom_tables.css"]

autodoc_mock_imports = [
    "win32com", 
    "win32com.client", 
    "pythoncom",
    "geopandas",
    "shapely",
    "fiona",
    "pyproj",
]

latex_documents = [
    (master_doc, "esapp.tex", "ESA++ Documentation", author, "manual"),
]

latex_elements = {
    "pointsize": "10pt",
    "fncychap": r"\usepackage[Bjornstrup]{fncychap}",
    "fontpkg": r"""
\usepackage{charter}
\usepackage[scaled=0.9]{inconsolata}
""",
    "preamble": r"""
\setcounter{tocdepth}{3}
\usepackage{mathrsfs}
\usepackage{breakurl}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{multirow}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{array}
\usepackage{tabularx}
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable}

% Define a modern color palette
\definecolor{linkblue}{RGB}{0, 83, 155}
\definecolor{codebackground}{RGB}{250, 250, 252}
\definecolor{codeborder}{RGB}{220, 220, 230}
\definecolor{headingblue}{RGB}{30, 60, 114}
\definecolor{noteblue}{RGB}{232, 244, 253}
\definecolor{noteborder}{RGB}{66, 165, 245}
\definecolor{warningyellow}{RGB}{255, 249, 230}
\definecolor{warningborder}{RGB}{255, 183, 77}
\definecolor{tipgreen}{RGB}{232, 245, 233}
\definecolor{tipborder}{RGB}{102, 187, 106}

% Sphinx code-block styling
\sphinxsetup{
    verbatimwithframe=false,
    VerbatimColor={RGB}{250,250,252},
    VerbatimBorderColor={RGB}{220,220,230},
    InnerLinkColor={RGB}{0,83,155},
    OuterLinkColor={RGB}{0,83,155},
    noteBgColor={RGB}{232,244,253},
    noteBorderColor={RGB}{66,165,245},
    warningBgColor={RGB}{255,249,230},
    warningBorderColor={RGB}{255,183,77},
    importantBgColor={RGB}{255,243,224},
    importantBorderColor={RGB}{255,152,0},
    tipBgColor={RGB}{232,245,233},
    tipBorderColor={RGB}{102,187,106},
    hintBgColor={RGB}{232,245,233},
    hintBorderColor={RGB}{102,187,106}
}

% Modern admonition styling - override Sphinx defaults
\renewenvironment{sphinxnote}[1]{%
  \begin{tcolorbox}[
    enhanced,
    breakable,
    colback=noteblue,
    colframe=noteborder,
    boxrule=0pt,
    leftrule=3pt,
    arc=0pt,
    outer arc=0pt,
    left=10pt,
    right=10pt,
    top=8pt,
    bottom=8pt,
    before skip=10pt,
    after skip=10pt
  ]
  \textbf{\sffamily\textcolor{noteborder}{#1}}\par\smallskip
}{\end{tcolorbox}}

\renewenvironment{sphinxwarning}[1]{%
  \begin{tcolorbox}[
    enhanced,
    breakable,
    colback=warningyellow,
    colframe=warningborder,
    boxrule=0pt,
    leftrule=3pt,
    arc=0pt,
    outer arc=0pt,
    left=10pt,
    right=10pt,
    top=8pt,
    bottom=8pt,
    before skip=10pt,
    after skip=10pt
  ]
  \textbf{\sffamily\textcolor{warningborder}{#1}}\par\smallskip
}{\end{tcolorbox}}

\renewenvironment{sphinxhint}[1]{%
  \begin{tcolorbox}[
    enhanced,
    breakable,
    colback=tipgreen,
    colframe=tipborder,
    boxrule=0pt,
    leftrule=3pt,
    arc=0pt,
    outer arc=0pt,
    left=10pt,
    right=10pt,
    top=8pt,
    bottom=8pt,
    before skip=10pt,
    after skip=10pt
  ]
  \textbf{\sffamily\textcolor{tipborder}{#1}}\par\smallskip
}{\end{tcolorbox}}

\renewenvironment{sphinxtip}[1]{%
  \begin{tcolorbox}[
    enhanced,
    breakable,
    colback=tipgreen,
    colframe=tipborder,
    boxrule=0pt,
    leftrule=3pt,
    arc=0pt,
    outer arc=0pt,
    left=10pt,
    right=10pt,
    top=8pt,
    bottom=8pt,
    before skip=10pt,
    after skip=10pt
  ]
  \textbf{\sffamily\textcolor{tipborder}{#1}}\par\smallskip
}{\end{tcolorbox}}

% Compact lists with slight breathing room
\setlist{nosep, itemsep=2pt}
\setlength{\parskip}{0.4em}
\setlength{\parindent}{0pt}

% Table styling
\renewcommand{\arraystretch}{1.25}
\setlength{\tabcolsep}{5pt}

% Modern header/footer with clean lines
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{gray}{\nouppercase{\leftmark}}}
\fancyhead[R]{\small\textcolor{gray}{\thepage}}
\fancyfoot[C]{\footnotesize\textcolor{gray}{ESA++ Documentation}}
\renewcommand{\headrulewidth}{0.5pt}
\renewcommand{\footrulewidth}{0pt}

% Style the head rule
\renewcommand{\headrule}{\vspace{-4pt}\hbox to\headwidth{\color{codeborder}\leaders\hrule height 0.5pt\hfill}}

% Style for DataFrame/table output in notebooks
\renewcommand{\sphinxstyletheadfamily}{\sffamily\bfseries\small}
""",
    "figure_align": "H",
    "sphinxsetup": "hmargin={1in,1in}, vmargin={1in,1in}",
}

# Disable the module index in PDF (it's not useful)
latex_domain_indices = False
