describe("Panel autenticado (stub API)", () => {
  beforeEach(() => {
    cy.loginAsStub();
  });

  it("carga el dashboard con sesión stub", () => {
    cy.location("pathname").should("eq", "/dashboard");
    cy.contains(/panel|dashboard|resumen|overview|actividad/i).should(
      "be.visible",
    );
  });

  it("navega a Documentos desde el sidebar", () => {
    cy.contains("a", /documentos|documents/i).click();
    cy.location("pathname").should("eq", "/dashboard/documentos");
  });

  it("navega a Embeddings / grafo", () => {
    cy.contains("a", /embeddings/i).click();
    cy.location("pathname").should("eq", "/dashboard/embeddings");
  });

  it("navega a Flujo RAG", () => {
    cy.contains("a", /flujo rag|rag flow/i).click();
    cy.location("pathname").should("eq", "/dashboard/flujo-rag");
  });

  it("navega a Organización", () => {
    cy.contains("a", /^organización$|^organization$/i).click();
    cy.location("pathname").should("eq", "/dashboard/organization");
  });

  it("navega a Evaluación", () => {
    cy.contains("a", /^evaluación$|^evaluation$/i).click();
    cy.location("pathname").should("eq", "/dashboard/evaluacion");
  });

  it("navega a Validación humana", () => {
    cy.contains("a", /validación humana|human validation/i).click();
    cy.location("pathname").should("eq", "/dashboard/validacion");
  });

  it("abre Ajustes desde el sidebar", () => {
    cy.contains("a", /^ajustes$|^settings$/i).click();
    cy.location("pathname").should("eq", "/dashboard/settings");
  });

  it("abre Documentación de ayuda", () => {
    cy.contains("a", /^docs$/i).click();
    cy.location("pathname").should("eq", "/dashboard/docs");
  });

  it("abre Soporte", () => {
    cy.contains("a", /^soporte$|^support$/i).click();
    cy.location("pathname").should("eq", "/dashboard/support");
  });
});
