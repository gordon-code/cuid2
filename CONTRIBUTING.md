# Contribute

This is the contribute.md of our project. Great to have you here. 
Here are a few ways you can help make this project better!

If you want to add an issue or pull request, please ensure that 
the [existing issues](https://github.com/gordon-code/cuid2/issues) 
don't already cover your question or contribution.

## Installation

We recommend using [`pdm`](https://pdm.fming.dev/latest/) 
to isolate dependencies for development and reuse existing workflows. 
This guide assumes that you have already installed `pdm`.

Clone the repository (alternatively, if you plan on making a pull request and 
are not in the cuid2.py organisation, use the [GitHub page](https://github.com/gordon-code/cuid2) 
to create your own fork)
```bash
$ git clone git@github.com:gordon-code/cuid2.git
$ cd cuid2
```

Ensure that you have installed the package and development dependencies:
```bash
$ pdm install
```

And finally create a separate branch to begin work
```bash
$ git checkout -b my-new-feature
```

## Preparing your commit

We rely on a number of formatters, linters, and tests to ensure that 
the codebase is consistent and free from regressions. Running with
`pdm run lint-fast` enables quick updates to files during development.

Prior to committing, we encourage running the following commands in
order for your pull request to be accepted:
```bash
$ pdm run tox
```

The GitHub Action will _also_ run `pdm run testing-slow` to catch any
collision regressions. You may also run it locally. The test takes
approximately 40 minutes.

## Submitting Pull Requests

Pull requests are welcomed! We'd like to review the design and implementation as early as
possible so please submit the pull request even if it's not 100%.
Let us know the purpose of the change and list the remaining items which need to be
addressed before merging. Finally, PR's should include unit tests and documentation
where appropriate.

**If you have further questions, contact us at dev@gordoncode.dev**
