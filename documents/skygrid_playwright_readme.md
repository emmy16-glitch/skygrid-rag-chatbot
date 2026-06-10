# SkyGrid Playwright QA Automation Framework

This project is an automated testing framework built for the SkyGrid web application using Playwright and TypeScript.

The framework tests key areas of the SkyGrid platform, including login validation, dashboard visibility, dashboard interactions, module navigation, and basic user interface checks.

## Project Overview

SkyGrid is a Ground Control Station and drone operations management platform. This QA automation framework was created to verify important workflows and ensure the application remains stable after updates.

## Tools Used

* Playwright
* TypeScript
* Node.js
* Git and GitHub
* GitHub Actions

## Test Coverage

The framework currently includes tests for:

* Valid user login
* Invalid login validation
* Dashboard loading
* Dashboard sidebar navigation
* Dashboard search interaction
* Recent missions section
* Pagination visibility
* Recent alert feed
* Session refresh
* Organization module
* Fleet & Assets module
* Mission Center module
* Live Operations module
* People & Access module
* Device & Security module
* Audit Logs module
* System Settings/Profile module

## Project Structure

```text
ai-qa-framework/
├── pages/
│   ├── LoginPage.ts
│   └── DashboardPage.ts
├── tests/
│   ├── dashboard-pom.spec.ts
│   ├── dashboard-interactions.spec.ts
│   ├── login-validation.spec.ts
│   ├── skygrid-modules.spec.ts
│   └── save-auth.spec.ts
├── .github/
│   └── workflows/
│       └── playwright.yml
├── playwright.config.ts
├── package.json
└── README.md
```

## How to Run the Tests Locally

Install dependencies:

```bash
npm install
```

Install Playwright browser:

```bash
npx playwright install chromium
```

Run all Chromium tests:

```bash
npx playwright test --project=chromium
```

Open the Playwright HTML report:

```bash
npx playwright show-report
```

## GitHub Actions CI

This project uses GitHub Actions to run tests automatically whenever code is pushed to the main branch.

The CI workflow runs:

```bash
npx playwright test --project=chromium
```

This helps confirm that the tests pass both locally and in the GitHub environment.

## Current Status

* Local tests passing
* GitHub Actions CI passing
* 21 automated tests added
* Playwright HTML report generated after each test run

## Summary

This project demonstrates a practical QA automation workflow using Playwright. It includes test planning, page object usage, dashboard testing, module testing, validation testing, Git version control, and CI integration with GitHub Actions.
