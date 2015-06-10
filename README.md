# Packal.org Alfred Workflow Search #

Search [Packal.org](http://www.packal.org/)'s collection of workflows from the comfort of Alfred.

![](https://raw.githubusercontent.com/deanishe/alfred-packal-search/b984fd2814a4e60be8c12c70f7ea38238000bcc3/demo.gif "")

## Usage ##

- `packal workflows [query]` — View/search for workflows by name/category/author/tag
	+ `↩` — Open workflow page on Packal.org in your browser
	+ `⌘+↩` — View/search workflows by the same author
- `packal tags [query]` — View/search workflow tags
	+ `↩` or `⇥` — View/search workflows with selected tag
- `packal categories [query]` — View/search workflow categories
	+ `↩` or `⇥` — View/search workflows in selected category
- `packal authors [query]` — View/search workflow authors
	+ `↩` or `⇥` — View/search workflows by selected author
    + `⌘+↩` — Add this author to the status blacklist. This means workflows
      by this author won't be shown in the update status list. Useful for
      hiding your own workflows, which you presumably don't update via Packal.
- `packal versions [query]` — View/search OS X versions and compatible workflows
	+ `↩` or `⇥` — View/search workflows compatible with selected OS X version
- `packal status` — Show a list of workflows that are out-of-date (❗) or are available on Packal.org, but were installed from elsewhere (❓)

## Icons ##

Sometimes, an icon is shown after a workflow's name. They have the following meanings:

| Icon |                      Meaning                      |
|------|---------------------------------------------------|
| ✅    | Up-to-date                                        |
| ❗    | Update available                                  |
| ❓    | Available on Packal, but not installed from there |

## Thanks, Licence ##

Thanks to [Shawn Patrick Rice](http://www.packal.org/) for building [Packal.org](http://www.packal.org/).

Much use made of [docopt](https://github.com/docopt/docopt) and [Alfred-Workflow](https://github.com/deanishe/alfred-workflow).

This workflow, excluding the Packal icon, is released under the [MIT Licence](http://opensource.org/licenses/MIT).

The Packal icon is the property of [Shawn Patrick Rice](http://www.packal.org/).
