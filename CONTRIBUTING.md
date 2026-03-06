# Contributing to AgenticAI

First off, thank you for considering contributing to AgenticAI! It's people like you that make the open-source community such a great place to learn, inspire, and create.

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open-source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## How Can I Contribute?

### Reporting Bugs
Bugs are tracked as GitHub issues. When creating an issue, please explain the problem and include additional details to help maintainers reproduce the problem:

*   **Use a clear and descriptive title** for the issue to identify the problem.
*   **Describe the exact steps which reproduce the problem** in as many details as possible.
*   **Provide specific examples to demonstrate the steps**, such as links to files, or copy-paste snippets.
*   **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
*   **Explain which behavior you expected to see instead and why.**
*   **Include screenshots and animated GIFs** which show you following the described steps and clearly demonstrate the problem.
*   **Include your environment details** (OS, Python version, Docker version, etc.).

### Suggesting Enhancements
Enhancement suggestions are also tracked as GitHub issues. When creating an enhancement suggestion, please include:

*   **Use a clear and descriptive title** for the issue to identify the suggestion.
*   **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
*   **Describe the current behavior** and **explain which behavior you expected to see instead** and why.
*   **Explain why this enhancement would be useful** to most AgenticAI users.

### Pull Requests
The process described here has several goals:
*   Maintain AgenticAI's quality
*   Fix problems that are important to users
*   Engage the community in working toward the best possible AgenticAI
*   Enable a sustainable system for AgenticAI's maintainers to review contributions

Please follow these steps to have your contribution considered by the maintainers:

1.  **Fork** the repository and **clone** it locally.
2.  **Create a new branch** describing the feature or fix (`git checkout -b feature/your-feature-name` or `fix/your-fix-name`).
3.  **Make your changes**, focusing on a single, well-defined objective. Keep the changes small and focused.
4.  **Test your changes.** Ensure your code works properly and does not break existing functionality. Run the app locally and test the UI and backend thoroughly.
5.  **Commit your changes** using descriptive commit messages (`git commit -m 'Add some feature'`).
6.  **Push to the branch** (`git push origin feature/your-feature-name`).
7.  **Open a Pull Request** against the `main` branch. Describe your changes in detail in the PR description, including relevant issue numbers if applicable.

## Development Setup
To set up AgenticAI for local development, refer to the **Setup Process** section in our `README.md`. We heavily recommend using the **Docker** approach for a consistent environment.

### Code Style Guide
*   **Python:** We loosely follow PEP 8 guidelines. For consistency, please format your code appropriately. We encourage using tools like `black` or `flake8`.
*   **Documentation:** Please ensure that any new functions, classes, or significant logic changes include descriptive docstrings.
*   **Type Hinting:** Please use Python type hints (`List`, `Dict`, `Optional`, etc.) where appropriate to improve code readability and maintainability, especially in the LangGraph schemas and components.

## Need Help?
If you have any questions or need help, feel free to open a discussion or reach out to the maintainers by opening an issue labeled `question`.

Thank you for contributing!
