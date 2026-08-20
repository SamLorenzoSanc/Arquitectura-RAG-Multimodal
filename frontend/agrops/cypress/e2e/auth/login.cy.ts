describe("Autenticación", () => {
  it("muestra el formulario de login", () => {
    cy.visit("/login");
    cy.contains("h2", /iniciar sesión|sign in/i).should("be.visible");
    cy.get('input[type="email"]').should("be.visible");
    cy.get('input[type="password"]').should("be.visible");
    cy.contains("button", /entrar|sign in|log in/i).should("be.visible");
  });

  it("exige email y contraseña", () => {
    cy.visit("/login");
    cy.contains("button", /entrar|sign in|log in/i).click();
    cy.contains(/introduce tu correo|introduce tu contraseña|required/i).should(
      "be.visible",
    );
  });

  it("enlaza a registro desde login", () => {
    cy.visit("/login");
    cy.contains("a", /crear cuenta|create account|register/i).click();
    cy.location("pathname").should("eq", "/register");
  });

  it("redirige /dashboard a /login sin sesión", () => {
    cy.clearLocalStorage();
    cy.visit("/dashboard");
    cy.location("pathname").should("eq", "/login");
  });

  it("muestra la pantalla de registro", () => {
    cy.visit("/register");
    cy.get('input[type="email"], input[name="email"]').should("exist");
    cy.contains(/registro|register|crear/i).should("be.visible");
  });
});
