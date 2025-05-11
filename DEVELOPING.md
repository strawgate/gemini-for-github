## Usage in this Development Repository

In this development repository, instead of using the action directly, we will install the dependencies and run the Python script. This is useful for testing changes locally before publishing a new version of the action.

#### Triggering via Issue Comment

```yaml
name: Gemini Action on Issue Comment (Dev)

on:
  issue_comment:
    types: [created]

jobs:
  run_gemini_action:
    runs-on: ubuntu-latest
    if: 
      contains(github.event.comment.body, '/gemini')
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x' # Specify the Python version you want to use

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run Gemini Action CLI
        run: |
          poetry run python src/gemini_for_github/main.py \
            --gemini-api-key ${{ secrets.GEMINI_API_KEY }} \
            --github-token ${{ secrets.GITHUB_TOKEN }} \
            --github-owner ${{ github.repository_owner }} \
            --github-repo ${{ github.event.repository.name }} \
            --github-issue-number ${{ github.event.issue.number }} \
            --user-question "${{ github.event.comment.body }}"
```

#### Triggering via Pull Request

```yaml
name: Gemini Action on Pull Request (Dev)

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  run_gemini_action:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x' # Specify the Python version you want to use

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run Gemini Action CLI
        run: |
          poetry run python src/gemini_for_github/main.py \
            --gemini-api-key ${{ secrets.GEMINI_API_KEY }} \
            --github-token ${{ secrets.GITHUB_TOKEN }} \
            --github-owner ${{ github.repository_owner }} \
            --github-repo ${{ github.event.repository.name }} \
            --github-pr-number ${{ github.event.pull_request.number }} \
            --user-question "gemini review this pull request." # Default question for PRs