/// <reference types="cypress" />

function encodeJwtPart(value: object): string {
  return btoa(JSON.stringify(value))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function buildStubJwt(): string {
  const header = encodeJwtPart({ alg: "none", typ: "JWT" });
  const payload = encodeJwtPart({
    sub: "00000000-0000-4000-8000-0000000000e2",
    email: "e2e@agrops.test",
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  });
  return `${header}.${payload}.e2e`;
}

const STUB_ORG = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "AgroTech",
  description: "Organización E2E",
  status: "ACTIVE",
  is_global: true,
  departments: [],
  members: [],
};

const EMPTY_ANALYTICS = {
  user_id: "00000000-0000-4000-8000-0000000000e2",
  totals: {
    documents: 0,
    conversations: 0,
    questions: 0,
    projects: 0,
    organizations: 1,
    api_calls: 0,
    active_tokens: 0,
    support_tickets: 0,
    documents_week: 0,
    questions_week: 0,
  },
  activity: [],
  recent_documents: [],
  recent_conversations: [],
  projects: [],
  timeline: [],
};

Cypress.Commands.add("stubBackend", () => {
  cy.intercept("GET", "**/api/v1/**", (req) => {
    const path = req.url.replace(/^https?:\/\/[^/]+/, "");

    if (path.includes("/auth/me")) {
      req.reply({
        statusCode: 200,
        body: {
          email: "e2e@agrops.test",
          name: "Usuario E2E",
          is_admin: true,
          job_title: "QA",
          phone: null,
          island: "Tenerife",
          has_avatar: false,
        },
      });
      return;
    }

    if (/\/organization\/?(\?|$)/.test(path) || path.endsWith("/organization")) {
      req.reply({ statusCode: 200, body: [STUB_ORG] });
      return;
    }

    if (path.includes("/organization/")) {
      req.reply({ statusCode: 200, body: STUB_ORG });
      return;
    }

    if (path.includes("/account/support")) {
      req.reply({
        statusCode: 200,
        body: { tickets: [], is_admin: false },
      });
      return;
    }

    if (path.includes("/account/admins")) {
      req.reply({ statusCode: 200, body: [] });
      return;
    }

    if (path.includes("/account/analytics") || path.includes("/account/usage")) {
      req.reply({ statusCode: 200, body: EMPTY_ANALYTICS });
      return;
    }

    if (path.includes("/account/")) {
      req.reply({ statusCode: 200, body: EMPTY_ANALYTICS });
      return;
    }

    if (path.includes("/documents") || path.includes("/knowledge")) {
      req.reply({ statusCode: 200, body: [] });
      return;
    }

    req.reply({ statusCode: 200, body: {} });
  }).as("api");
});

Cypress.Commands.add("loginAsStub", () => {
  const token = buildStubJwt();
  cy.stubBackend();
  cy.visit("/dashboard", {
    onBeforeLoad(win) {
      win.localStorage.setItem("token", token);
    },
  });
});

declare global {
  namespace Cypress {
    interface Chainable {
      stubBackend(): Chainable<void>;
      loginAsStub(): Chainable<void>;
    }
  }
}

export {};
