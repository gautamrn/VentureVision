DEMO_PITCHES = [
    {
        "id": "flakeguard",
        "category": "Dev-tools SaaS",
        "title": "Flakeguard",
        "tagline": "Detects and quarantines flaky tests before they block a merge.",
        "pitch": """Flakeguard: stop flaky tests from blocking your merges.

Problem: Flaky tests pass and fail on the same code. Every red build triggers a rerun, a Slack thread, and an engineer digging through logs to decide whether the failure is real. Engineers at companies with large CI pipelines lose up to 20% of their week to flaky tests, and teams learn to ignore red builds, which is how real regressions ship.

Product: Flakeguard is a GitHub App and CI plugin for GitHub Actions, CircleCI, and Buildkite. It ingests JUnit test reports from every run, scores each test's flakiness from its pass/fail history on unchanged code, and automatically quarantines tests above a threshold so they stop blocking merges while still running in the background. Each quarantined test gets a ticket with the failure signatures, the commits where it started flaking, and the likely cause (timing, test order, shared state, or network).

Why now: Monorepos and parallel CI have multiplied test counts. A 5,000-test suite with a 0.1% flake rate per test fails most runs.

Market: The DevOps tools market is worth over $10B, and no existing tool automatically quarantines flaky tests; today teams maintain skip lists by hand.

Business model: $15 per active developer per month, free for open source. Land with one team, expand across the org.

Traction: 14 design partners, 3 paying teams, $4,200 MRR, quarantining 1,900 tests across 2.3M CI runs.

Team: Ex-staff engineers from a large CI provider's build infrastructure team.

Ask: Raising a $2.5M seed to build the test-ownership graph and expand to Jenkins and GitLab CI.""",
    },
    {
        "id": "pantry",
        "category": "Consumer app",
        "title": "Pantry",
        "tagline": "Turns grocery receipts into a weekly meal plan that uses what you already bought.",
        "pitch": """Pantry: cook what you bought before it goes bad.

Problem: The average US household throws away about 30% of the food it buys, roughly $1,500 a year. People buy groceries with good intentions, forget what is in the fridge, and order takeout while vegetables rot.

Product: Pantry is an iOS and Android app. Snap a photo of your grocery receipt (or connect Instacart and Walmart accounts) and Pantry builds a live inventory of your kitchen with estimated expiry dates. Every Sunday it generates a weekly meal plan that prioritizes ingredients about to expire, fits your household size and dietary preferences, and produces a short shopping list for what is missing. Push reminders flag food that needs to be used tomorrow.

Differentiation: Meal-planning apps start from recipes and send you shopping. Pantry starts from what you already own. No other app builds the plan from your receipts.

Market: Meal-planning apps are a $3B global market growing over 12% a year, alongside a $100B+ US online grocery market.

Business model: Freemium. Free inventory and reminders; Pantry Plus at $6.99/month adds weekly plans, nutrition targets, and family sharing. Grocery retailer affiliate revenue on shopping lists.

Traction: 38,000 downloads in a 5-month beta, 9,400 monthly active users, 6.1% free-to-paid conversion, 41% week-4 retention.

Team: Former product lead at a food-delivery app and an ML engineer who built receipt OCR at a fintech.

Ask: Raising $1.8M pre-seed to launch Android and retailer integrations.""",
    },
    {
        "id": "thermalith",
        "category": "Climate hardware",
        "title": "Thermalith",
        "tagline": "Sand-based thermal batteries that replace gas boilers for industrial process heat.",
        "pitch": """Thermalith: store cheap renewable power as heat, deliver it to factories on demand.

Problem: Industrial process heat accounts for about 20% of global final energy consumption and is still overwhelmingly produced by burning natural gas and coal. Electrifying it with heat pumps works below about 150°C, but food processing, chemicals, paper, and cement need steam and hot air at 200 to 1,000°C, around the clock.

Product: Thermalith is a containerized thermal battery that charges from the grid when electricity is cheapest (often surplus wind and solar), heats a bed of industrial sand to 600°C with resistive elements, and discharges steam or hot air on demand. One unit stores 10 MWh of heat and drops into an existing boiler room as a direct replacement for a gas boiler.

Technology: Sand is abundant, non-toxic, and costs under $40 per ton. Our storage medium costs under $15 per kWh of capacity, a fraction of lithium-ion batteries. Thermalith is the first company to commercialize a sand-based thermal battery.

Market: Industrial heat is a $200B+ annual fuel market. We start with food and beverage plants in Europe and California, where gas prices and carbon costs are highest.

Business model: Heat-as-a-service contracts: we own the unit and sell heat per MWh at a price below the customer's current gas-plus-carbon cost, with 10-year terms.

Traction: 1 MWh pilot running at a dairy plant for 7 months with 94% round-trip thermal efficiency; LOIs for 120 MWh across 6 sites.

Team: Thermal engineers from a concentrated solar power company and a former plant manager from a large food manufacturer.

Ask: Raising a $6M seed to build the first 10 MWh commercial unit.""",
    },
]
