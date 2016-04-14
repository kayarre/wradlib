# -*- coding: utf-8 -*-
#
# wradlib documentation build configuration file, created by
# sphinx-quickstart on Wed Oct 26 13:48:08 2011.
# adapted with code from
# https://github.com/ARM-DOE/pyart/blob/master/doc/source/conf.py
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import glob

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.napoleon',
              'sphinx.ext.todo',
              'sphinx.ext.coverage',
              # 'sphinx.ext.pngmath',
              'sphinx.ext.mathjax',
              'sphinx.ext.autosummary',
              'sphinx.ext.intersphinx',
              'sphinxcontrib.bibtex',
              'numpydoc',
              'matplotlib.sphinxext.plot_directive',
              'nbsphinx',
              'IPython.sphinxext.ipython_console_highlighting',
              ]

# just generate normal png
plot_formats = ['png']

mathjax_path = ("https://cdn.mathjax.org/mathjax/latest/MathJax.js?"
                "config=TeX-AMS-MML_HTMLorMML")

# + other custom stuff for inline math, such as non-default math fonts etc.
pngmath_latex_preamble = r'\usepackage[active]{preview}'
pngmath_use_preview = True

# get all rst files, do it manually
rst_files = glob.glob('*.rst')
autosummary_generate = rst_files

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'wradlib'
copyright = u'2011-2016, wradlib developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# todo: clean this up
import wradlib  # noqa

# The short X.Y version (including the .devXXXX suffix if present)
# version = re.sub(r'^(\d+\.\d+)\.\d+(.*)', r'\1\2', wradlib.__version__)
# if 'dev' not in version:
#    # strip all other suffixes
#    version = re.sub(r'^(\d+\.\d+).*?$', r'\1', version)
# else:
#    # retain the .dev suffix, but clean it up
#    version = re.sub(r'(\.dev\d*).*?$', r'\1', version)
#    pass

# The full version, including alpha/beta/rc tags.
version = wradlib.__version__
release = wradlib.__version__

print("RELEASE, VERSION", release, version)

# full wradlib version in CI built docs
if 'CI' in os.environ and os.environ['CI'] == 'true':
    version = release

# # get current version from file
# with open("../../version") as f:
#     VERSION = f.read()
#     VERSION = VERSION.strip()
#     MAJOR, MINOR, BUGFIX = VERSION.split(".")
#
# # The short X.Y version.
# version = '%s.%s' % (MAJOR, MINOR)
# # The full version, including alpha/beta/rc tags.
# release = '%s.%s.%s' % (MAJOR, MINOR, BUGFIX)
#
# project = project + " v" + release

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# exclude_patterns = []
exclude_patterns = ['_build', '**.ipynb_checkpoints']

# The reST default role (used for this markup: `text`)
# to use for all documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'

import sphinx_rtd_theme  # noqa

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_style = 'wradlib.css'
html_theme_options = {'sticky_navigation': True}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {"sidebarbgcolor": "black",
#                      "relbarbgcolor": "black",
#                      "headtextcolor": "#4A4344",
#                      "footerbgcolor": "black" }

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = project

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "wradlib"

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = "images/wradliblogo_small.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}
# html_sidebars = {
#   '**': ['globaltoc.html', 'sourcelink.html', 'searchbox.html'],
#   'using/windows': ['windowssidebar.html', 'searchbox.html'],
# }

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'wradlibdoc'

# -- Options for LaTeX output -------------------------------------------------

# The paper size ('letter' or 'a4').
# latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
# latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
# author, documentclass [howto/manual]).
latex_documents = [('index', 'wradlib.tex', u'wradlib Documentation',
                    u'wradlib developers', 'manual'), ]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Additional stuff for the LaTeX preamble.
# latex_preamble = ''

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True

intersphinx_mapping = {
    'python': ('https://docs.python.org/2', None),
    'numpy': ('https://docs.scipy.org/doc/numpy/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
    'matplotlib': ('http://matplotlib.org/', None),
    'sphinx': ('http://sphinx-doc.org', None),
}

# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'wradlib', u'wradlib Documentation',
     [u'wradlib developers'], 1)
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = False

# multiple releases section
# if on CI get TAGGED_VERSIONS otherwise empty dict
releases = []
if 'CI' in os.environ and os.environ['CI'] == 'true':
    if 'TAGGED_VERSIONS' in os.environ:
        for ver in os.environ['TAGGED_VERSIONS'].split("\n"):
            releases.append([ver, ver])
        releases.sort(reverse=True)
# if tagged release insert tag
if 'TAG' in os.environ and os.environ['TAG']:
    releases.insert(0, [os.environ['TAG'], os.environ['TAG']])
# have latest anyway
releases.insert(0, ['latest', 'latest'])
# push releases into html_context
html_context = {'releases': releases, }
