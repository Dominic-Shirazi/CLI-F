# Master_Plan_requirements.md

This document contains the canonical question reference for the Project Genesis interviewer. These questions are designed to gather all necessary information to generate a complete EndToEndDev project structure.

## 1. Project Core & Identity
- What is the official name of the project?
- Give a one-sentence elevator pitch: what problem does this solve and for whom?
- What are the 3 most important high-level goals for this project?
- Who is the primary user (e.g., developer, end-consumer, internal admin)?
- What is the primary programming language and main framework (e.g., Python/FastAPI, TypeScript/Next.js)?

## 2. User Experience & Interface
- Will this have a UI? If so, is it Web, Mobile, or CLI?
- What is the "happy path" a user takes to get value from the app?
- List 3-5 key screens or interface components (e.g., Dashboard, Login Page, Settings).
- Do you have a preferred UI library or design system (e.g., Tailwind CSS, Material UI, Bootstrap)?
- Should the UI be "modern/polished" or "functional/minimalist" for the first version?

## 3. Features & Functionality
- List the top 3 "must-have" features for the MVP.
- Are there any specific "nice-to-have" features we should keep in mind for later?
- Does the app require user authentication (login/signup)?
- If yes to auth, what method (Email/Password, Google OAuth, Magic Link)?
- Are there different user roles (e.g., Admin vs. Regular User)?

## 4. Data & State Management
- What are the main data entities (e.g., Users, Posts, Projects, Orders)?
- How do these entities relate to each other?
- What database do you prefer (e.g., PostgreSQL, MongoDB, SQLite)?
- Does the app need real-time updates (e.g., WebSockets, Supabase Realtime)?
- How complex is the client-side state (simple forms vs. complex interactive dashboards)?

## 5. External Integrations & APIs
- Will you be using any third-party APIs (e.g., Stripe, OpenAI, SendGrid)?
- Does the app need to integrate with existing services (e.g., Slack, GitHub, Discord)?
- Are there any specific webhooks the app needs to handle?
- Do you have any specific requirements for API documentation (e.g., Swagger/OpenAPI)?

## 6. Development & Tooling
- What is your preferred package manager (npm, yarn, pnpm, pip)?
- Do you have a preference for a testing framework (pytest, Jest, Vitest)?
- Should we set up specific linting or formatting rules (ESLint, Prettier, Ruff)?
- Do you want a CI/CD pipeline configured (GitHub Actions, Vercel)?

## 7. Infrastructure & Deployment
- Where do you plan to host the application (Vercel, Railway, AWS, Heroku)?
- Are there any specific environment variables or secrets we need to account for?
- Does the app require any background workers or cron jobs?
- Do you need a staging environment or just production?

## 8. Project Milestones
- What is the very first thing that needs to be functional (Step 1)?
- Can you break down the development into 3-5 major steps or milestones?
- Is there a specific deadline or target date for the MVP?

## 9. Success & Quality Standards
- How will we know Step 1 is "done"? (e.g., "User can see a hello world page")
- What is the minimum test coverage required for a step to be approved?
- Are there any performance requirements (e.g., "Page loads in under 2 seconds")?
- What level of documentation is expected (README only, full API docs)?
