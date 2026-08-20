describe("Landing pública", () => {
  beforeEach(() => {
    cy.visit("/");
  });

  it("carga el hero de AgroPS", () => {
    cy.contains("h1", /ecosistema inteligente/i).should("be.visible");
    cy.contains("a", /empezar|start|ahora/i).should("be.visible");
  });

  it("navega a login desde el CTA principal", () => {
    cy.contains("a", /comenzar ahora|start now|empezar ahora/i).click();
    cy.location("pathname").should("eq", "/login");
    cy.contains("h2", /iniciar sesión|sign in/i).should("be.visible");
  });

  it("navega a registro desde el CTA secundario", () => {
    cy.contains("a", /crear cuenta|create account/i).first().click();
    cy.location("pathname").should("eq", "/register");
  });

  it("cambia el idioma a inglés desde el header", () => {
    cy.contains("button", "EN").click();
    cy.window()
      .its("localStorage")
      .invoke("getItem", "agrops-lang")
      .should("eq", "en");
    cy.reload();
    cy.document().its("documentElement.lang").should("eq", "en");
    cy.contains("h1", /intelligent ecosystem/i).should("be.visible");
    cy.contains("a", /get started/i).should("be.visible");
  });
});
