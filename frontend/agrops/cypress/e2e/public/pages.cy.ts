describe("Páginas públicas", () => {
  it("carga Acerca de", () => {
    cy.visit("/about");
    cy.contains(/acerca de|about/i).should("be.visible");
    cy.location("pathname").should("eq", "/about");
  });

  it("carga Sostenibilidad", () => {
    cy.visit("/sustainability");
    cy.contains(/sostenib|sustainab/i).should("be.visible");
  });

  it("carga Política de privacidad", () => {
    cy.visit("/privacy-policy");
    cy.contains(/privacidad|privacy/i).should("be.visible");
  });

  it("el header público enlaza login y registro", () => {
    cy.visit("/");
    cy.get("header").within(() => {
      cy.contains("a", /iniciar sesión|login|sign in/i).should(
        "have.attr",
        "href",
        "/login",
      );
      cy.contains("a", /empieza|empezar|get started|comenzar/i).should(
        "have.attr",
        "href",
        "/register",
      );
    });
  });

  it("el logo del header vuelve al inicio", () => {
    cy.visit("/about");
    cy.get("header a").first().click();
    cy.location("pathname").should("eq", "/");
  });
});
