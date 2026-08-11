import { useState, useEffect, useCallback, useMemo } from "react";
import {
  TrendingUp,
  BarChart3,
  Sun,
  Droplets,
  Sliders,
  RefreshCw,
  Info,
  CheckCircle2,
  Zap,
  MapPin,
  Calendar,
  ArrowUpRight,
  Leaf,
  AlertCircle,
  BookOpen,
  Activity,
  Fuel,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  ComposedChart,
  Line,
} from "recharts";

interface ForecastMetric {
  MAPE: number;
  RMSE: number;
  MAE?: number;
  AIC?: number;
  BIC?: number;
  execution_time_ms?: number;
}

interface ComparisonPoint {
  date: string;
  prophet_prediction: number;
  arimax_prediction: number;
}

interface HistoryPoint {
  date: string;
  price: number;
  max_temp: number;
  precipitation: number;
  oil_price: number;
}

interface CoeffRow {
  variable: string;
  label: string;
  unit: string;
  coefficient: number;
  direction: string;
  farmer_impact: string;
  course_link: string;
  pearson_corr: number;
}

interface AnalysisResponse {
  product_id: string;
  island: string;
  stationarity: {
    test: string;
    stationary: boolean;
    adf_stat: number | null;
    pvalue: number | null;
    interpretation: string;
    critical_values?: Record<string, number>;
    diff1?: { stationary: boolean; pvalue: number | null; interpretation: string };
  };
  exogenous_impact: {
    product: string;
    correlations: Record<string, number>;
    arimax_coefficients: CoeffRow[];
    sensitivity_shocks: {
      variable: string;
      label: string;
      shock: string;
      price_delta_eur: number;
      price_delta_pct: number;
    }[];
    aic: number;
    bic: number;
    narrative: string;
  };
  volatility_ewma: {
    lambda: number;
    latest_vol_pct: number;
    mean_vol_pct: number;
    series: { date: string; vol_pct: number }[];
  };
  history: HistoryPoint[];
  prophet_metrics: ForecastMetric;
  arimax_metrics: ForecastMetric;
  best_model: string;
  forecast_comparison: ComparisonPoint[];
  methodology: { topic: string; concept: string; applied: string }[];
}

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const PRODUCTS = [
  { id: "platano_canarias", name: "Plátano de Canarias IGP", unit: "€/kg" },
  { id: "aguacate_hass", name: "Aguacate (La Palma/Tenerife)", unit: "€/kg" },
  { id: "papa_bonita", name: "Papa Bonita de Color", unit: "€/kg" },
  { id: "tomate_canario", name: "Tomate de Exportación", unit: "€/kg" },
];

const ISLANDS = [
  { id: "Tenerife_Norte", name: "Tenerife Norte (Valle de La Orotava)" },
  { id: "Gran_Canaria_Sur", name: "Gran Canaria Sur (San Bartolomé)" },
  { id: "La_Palma", name: "La Palma (Valle de Aridane)" },
];

export default function AnalyticsPage() {
  const [selectedProduct, setSelectedProduct] = useState(PRODUCTS[0].id);
  const [selectedIsland, setSelectedIsland] = useState(ISLANDS[0].id);
  const [selectedModel, setSelectedModel] = useState<
    "prophet" | "arimax" | "compare"
  >("compare");
  const [months, setMonths] = useState(6);
  const [priceAdjustment, setPriceAdjustment] = useState(0);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);

  const productInfo =
    PRODUCTS.find((p) => p.id === selectedProduct) || PRODUCTS[0];

  const loadAnalysis = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/forecast/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: selectedProduct,
          island: selectedIsland,
          months: Number(months),
          price_adjustment: Number(priceAdjustment),
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Error en el análisis de precios");
      }
      const data: AnalysisResponse = await res.json();
      setAnalysis(data);
    } catch (err: any) {
      setError(err.message || "Error al conectar con la API de pronósticos");
    } finally {
      setIsLoading(false);
    }
  }, [selectedProduct, selectedIsland, months, priceAdjustment]);

  useEffect(() => {
    void loadAnalysis();
  }, [loadAnalysis]);

  const chartData = useMemo(() => {
    if (!analysis) return [];
    return analysis.forecast_comparison;
  }, [analysis]);

  const sensitivityData = useMemo(() => {
    return (
      analysis?.exogenous_impact.sensitivity_shocks.map((s) => ({
        name: s.label.replace(" acumulada", "").replace(" máxima", ""),
        impacto_pct: s.price_delta_pct,
        impacto_eur: s.price_delta_eur,
      })) ?? []
    );
  }, [analysis]);

  const avgPrice = useMemo(() => {
    if (!chartData.length) return "0.00";
    const key =
      selectedModel === "arimax" ? "arimax_prediction" : "prophet_prediction";
    const vals = chartData.map((c) =>
      selectedModel === "compare"
        ? (c.prophet_prediction + c.arimax_prediction) / 2
        : c[key],
    );
    return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2);
  }, [chartData, selectedModel]);

  const prophetMetrics = analysis?.prophet_metrics ?? null;
  const arimaxMetrics = analysis?.arimax_metrics ?? null;
  const bestModel = analysis?.best_model ?? "";

  return (
    <div className="min-h-screen space-y-8 bg-slate-50/50 p-8">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
            <TrendingUp size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Analítica de precios al agricultor
            </h1>
            <p className="text-sm text-slate-500">
              Series temporales · ARIMAX · Prophet · variables exógenas ·
              volatilidad EWMA
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-800">
            <Leaf size={14} /> Canarias · Open-Meteo · CL=F
          </span>
          <button
            onClick={() => void loadAnalysis()}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={isLoading ? "animate-spin text-emerald-600" : ""}
            />
            Re-ejecutar análisis
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle size={20} className="shrink-0" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Controles */}
      <div className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2 font-semibold text-slate-800">
            <Sliders size={18} className="text-emerald-600" />
            Parámetros del escenario
          </div>
          <span className="text-xs text-slate-400">POST /forecast/analysis</span>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Producto
            </label>
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800"
            >
              {PRODUCTS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <MapPin size={12} /> Zona
            </label>
            <select
              value={selectedIsland}
              onChange={(e) => setSelectedIsland(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800"
            >
              {ISLANDS.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Calendar size={12} /> Horizonte
            </label>
            <select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800"
            >
              <option value={3}>3 meses</option>
              <option value={6}>6 meses</option>
              <option value={12}>12 meses</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Vista del gráfico
            </label>
            <div className="flex rounded-2xl border border-slate-200 bg-slate-100 p-1">
              {(
                [
                  ["prophet", "Prophet"],
                  ["arimax", "ARIMAX"],
                  ["compare", "Comparar"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setSelectedModel(id)}
                  className={`flex-1 rounded-xl py-2 text-xs font-semibold transition ${
                    selectedModel === id
                      ? "bg-white text-emerald-700 shadow-sm"
                      : "text-slate-600"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-2">
          <div className="mb-2 flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-600">
              Shock en petróleo / flete (regressor exógeno):{" "}
              <span className="font-bold text-emerald-700">
                {priceAdjustment > 0
                  ? `+${priceAdjustment}%`
                  : `${priceAdjustment}%`}
              </span>
            </label>
          </div>
          <input
            type="range"
            min={-15}
            max={15}
            value={priceAdjustment}
            onChange={(e) => setPriceAdjustment(Number(e.target.value))}
            className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-200 accent-emerald-600"
          />
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Kpi
          title="Precio medio proyectado"
          value={`${avgPrice} ${productInfo.unit}`}
          hint={`Modelo activo: ${bestModel || "—"}`}
          icon={<BarChart3 size={24} />}
          tone="emerald"
        />
        <Kpi
          title="Mejor algoritmo (MAPE)"
          value={bestModel || "N/A"}
          hint="Prophet vs ARIMAX in-sample"
          icon={<Zap size={24} />}
          tone="blue"
        />
        <Kpi
          title="Margen de error"
          value={`± ${
            (bestModel === "ARIMAX" ? arimaxMetrics : prophetMetrics)?.MAPE?.toFixed(
              1,
            ) ?? "0.0"
          }%`}
          hint="MAPE sobre histórico"
          icon={<AlertCircle size={24} />}
          tone="purple"
        />
        <Kpi
          title="Volatilidad EWMA"
          value={`${analysis?.volatility_ewma.latest_vol_pct?.toFixed(2) ?? "—"}%`}
          hint={`λ=${analysis?.volatility_ewma.lambda ?? 0.94} · Tema 7`}
          icon={<Activity size={24} />}
          tone="amber"
        />
      </div>

      {/* Metodología TFM */}
      <div className="rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <BookOpen size={18} className="text-indigo-600" />
          <h2 className="text-lg font-bold text-slate-900">
            Metodología (asignatura de series temporales)
          </h2>
        </div>
        <p className="mb-4 text-sm text-slate-600">
          {analysis?.exogenous_impact.narrative ??
            "Cargando narrativa del modelo…"}
        </p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          {(analysis?.methodology ?? []).map((m) => (
            <div
              key={m.topic}
              className="rounded-2xl border border-indigo-100 bg-white/80 p-4"
            >
              <p className="text-xs font-bold uppercase tracking-wide text-indigo-600">
                {m.topic}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {m.concept}
              </p>
              <p className="mt-1 text-xs text-slate-500">{m.applied}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Estacionariedad + impacto */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
          <h3 className="mb-2 flex items-center gap-2 font-bold text-slate-900">
            <Info size={18} className="text-emerald-600" /> Estacionariedad (ADF)
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            Test de Dickey-Fuller aumentado sobre el precio mensual.
          </p>
          {analysis?.stationarity ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between rounded-xl bg-slate-50 px-3 py-2">
                <span className="text-slate-500">Estadístico ADF</span>
                <span className="font-bold text-slate-900">
                  {analysis.stationarity.adf_stat ?? "—"}
                </span>
              </div>
              <div className="flex justify-between rounded-xl bg-slate-50 px-3 py-2">
                <span className="text-slate-500">p-valor</span>
                <span className="font-bold text-slate-900">
                  {analysis.stationarity.pvalue ?? "—"}
                </span>
              </div>
              <div
                className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                  analysis.stationarity.stationary
                    ? "bg-emerald-50 text-emerald-800"
                    : "bg-amber-50 text-amber-800"
                }`}
              >
                {analysis.stationarity.stationary
                  ? "Serie estacionaria (p < 0.05)"
                  : "Posible raíz unitaria → se diferencia en ARIMAX (d=1)"}
              </div>
              <p className="text-xs leading-relaxed text-slate-600">
                {analysis.stationarity.interpretation}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Sin datos aún.</p>
          )}
        </div>

        <div className="lg:col-span-2 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
          <h3 className="mb-1 font-bold text-slate-900">
            Variables que afectan al precio del agricultor
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            Coeficientes ARIMAX + correlación de Pearson. Shock simulado: +10%
            en cada regressor.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-3 py-2">Variable</th>
                  <th className="px-3 py-2">Corr.</th>
                  <th className="px-3 py-2">Coef. β</th>
                  <th className="px-3 py-2">Shock +10%</th>
                  <th className="px-3 py-2">Impacto en finca</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(analysis?.exogenous_impact.arimax_coefficients ?? []).map(
                  (row) => {
                    const shock =
                      analysis?.exogenous_impact.sensitivity_shocks.find(
                        (s) => s.variable === row.variable,
                      );
                    return (
                      <tr key={row.variable} className="align-top">
                        <td className="px-3 py-3">
                          <p className="font-semibold text-slate-900">
                            {row.label}
                          </p>
                          <p className="text-[11px] text-indigo-600">
                            {row.course_link}
                          </p>
                        </td>
                        <td className="px-3 py-3 font-mono text-xs">
                          {row.pearson_corr.toFixed(3)}
                        </td>
                        <td className="px-3 py-3">
                          <span className="font-mono text-xs font-bold">
                            {row.coefficient.toFixed(4)}
                          </span>
                          <span className="ml-1 text-[10px] text-slate-500">
                            {row.direction}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-xs font-semibold">
                          {shock ? (
                            <span
                              className={
                                shock.price_delta_pct >= 0
                                  ? "text-emerald-700"
                                  : "text-rose-700"
                              }
                            >
                              {shock.price_delta_pct >= 0 ? "+" : ""}
                              {shock.price_delta_pct.toFixed(2)}% (
                              {shock.price_delta_eur >= 0 ? "+" : ""}
                              {shock.price_delta_eur.toFixed(3)} €)
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="max-w-[220px] px-3 py-3 text-xs text-slate-600">
                          {row.farmer_impact}
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Sensibilidad chart + histórico */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
          <h3 className="mb-1 font-bold text-slate-900">
            Sensibilidad del precio (shock +10%)
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            ¿Cuánto se mueve el precio si sube un 10% la temperatura, la lluvia
            o el petróleo?
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sensitivityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis
                  tick={{ fontSize: 11 }}
                  unit="%"
                  label={{
                    value: "Δ precio %",
                    angle: -90,
                    position: "insideLeft",
                    fontSize: 11,
                  }}
                />
                <Tooltip />
                <Bar
                  dataKey="impacto_pct"
                  name="Impacto %"
                  fill="#059669"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
          <h3 className="mb-1 font-bold text-slate-900">
            Histórico precio vs exógenas
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            Últimos meses: precio (€/kg), temperatura y petróleo.
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={analysis?.history ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => String(v).slice(0, 7)}
                />
                <YAxis yAxisId="left" tick={{ fontSize: 11 }} unit="€" />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 11 }}
                />
                <Tooltip />
                <Legend />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="price"
                  name="Precio"
                  stroke="#0f172a"
                  fill="#cbd5e1"
                  fillOpacity={0.35}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="max_temp"
                  name="Temp. °C"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="oil_price"
                  name="Petróleo $"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Forecast */}
      <div className="relative space-y-4 rounded-3xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-200/40">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-3xl bg-white/70 backdrop-blur-sm">
            <RefreshCw className="animate-spin text-emerald-600" size={32} />
          </div>
        )}
        <div className="flex flex-col justify-between gap-2 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Proyección ({productInfo.name})
            </h2>
            <p className="text-xs text-slate-500">
              Intervalos de confianza implícitos en cada modelo · horizonte{" "}
              {months} meses
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            {(selectedModel === "prophet" || selectedModel === "compare") && (
              <span className="flex items-center gap-1.5 text-emerald-700">
                <span className="inline-block h-3 w-3 rounded-full bg-emerald-500" />{" "}
                Prophet
              </span>
            )}
            {(selectedModel === "arimax" || selectedModel === "compare") && (
              <span className="flex items-center gap-1.5 text-blue-700">
                <span className="inline-block h-3 w-3 rounded-full bg-blue-500" />{" "}
                ARIMAX
              </span>
            )}
          </div>
        </div>
        <div className="h-80 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="prophetGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="arimaxGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} unit=" €" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  borderRadius: 16,
                  border: "1px solid #e2e8f0",
                }}
              />
              <Legend />
              {(selectedModel === "prophet" || selectedModel === "compare") && (
                <Area
                  type="monotone"
                  name="Prophet"
                  dataKey="prophet_prediction"
                  stroke="#10b981"
                  strokeWidth={3}
                  fill="url(#prophetGrad)"
                />
              )}
              {(selectedModel === "arimax" || selectedModel === "compare") && (
                <Area
                  type="monotone"
                  name="ARIMAX"
                  dataKey="arimax_prediction"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  fill="url(#arimaxGrad)"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Métricas + exógenas live */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40 lg:col-span-2">
          <h3 className="flex items-center gap-2 font-bold text-slate-900">
            <CheckCircle2 size={18} className="text-emerald-600" />
            Fiabilidad de los modelos
          </h3>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-4 py-3">Algoritmo</th>
                <th className="px-4 py-3">MAPE</th>
                <th className="px-4 py-3">RMSE</th>
                <th className="px-4 py-3">AIC/BIC</th>
                <th className="px-4 py-3">Recomendación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {prophetMetrics && (
                <tr>
                  <td className="px-4 py-3 font-semibold">Prophet</td>
                  <td className="px-4 py-3 font-bold text-emerald-600">
                    ±{prophetMetrics.MAPE.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {prophetMetrics.RMSE.toFixed(3)} {productInfo.unit}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">—</td>
                  <td className="px-4 py-3">
                    {bestModel === "Prophet" && (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                        Más exacto
                      </span>
                    )}
                  </td>
                </tr>
              )}
              {arimaxMetrics && (
                <tr>
                  <td className="px-4 py-3 font-semibold">ARIMAX</td>
                  <td className="px-4 py-3 font-bold text-blue-600">
                    ±{arimaxMetrics.MAPE.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {arimaxMetrics.RMSE.toFixed(3)} {productInfo.unit}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {arimaxMetrics.AIC != null
                      ? `AIC ${arimaxMetrics.AIC}`
                      : analysis?.exogenous_impact.aic
                        ? `AIC ${analysis.exogenous_impact.aic}`
                        : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {bestModel === "ARIMAX" && (
                      <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">
                        Más exacto
                      </span>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="space-y-3 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40">
          <h3 className="font-bold text-slate-900">Exógenas recientes</h3>
          <ExogRow
            icon={<Sun size={20} className="text-amber-500" />}
            title="Temperatura"
            subtitle={selectedIsland}
            value={
              analysis?.history?.length
                ? `${analysis.history[analysis.history.length - 1].max_temp}°C`
                : "—"
            }
          />
          <ExogRow
            icon={<Droplets size={20} className="text-blue-500" />}
            title="Precipitación"
            subtitle="mm / mes"
            value={
              analysis?.history?.length
                ? `${analysis.history[analysis.history.length - 1].precipitation} mm`
                : "—"
            }
          />
          <ExogRow
            icon={<Fuel size={20} className="text-slate-700" />}
            title="Petróleo CL=F"
            subtitle="Coste flete / insumos"
            value={
              analysis?.history?.length
                ? `$${analysis.history[analysis.history.length - 1].oil_price}`
                : "—"
            }
          />
          <div className="rounded-2xl bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-600">
            Mueve el slider de petróleo para simular un shock de coste y ver cómo
            ARIMAX y Prophet reaccionan en la proyección — típico escenario de
            riesgo para el margen del agricultor.
          </div>
        </div>
      </div>
    </div>
  );
}

function Kpi({
  title,
  value,
  hint,
  icon,
  tone,
}: {
  title: string;
  value: string;
  hint: string;
  icon: React.ReactNode;
  tone: "emerald" | "blue" | "purple" | "amber";
}) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-600",
    blue: "bg-blue-50 text-blue-600",
    purple: "bg-purple-50 text-purple-600",
    amber: "bg-amber-50 text-amber-600",
  };
  const hints = {
    emerald: "text-emerald-600",
    blue: "text-blue-600",
    purple: "text-purple-600",
    amber: "text-amber-600",
  };
  return (
    <div className="flex items-start justify-between rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/30">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </p>
        <h3 className="mt-2 text-3xl font-bold text-slate-900">{value}</h3>
        <p className={`mt-2 flex items-center gap-1 text-xs font-medium ${hints[tone]}`}>
          <ArrowUpRight size={14} /> {hint}
        </p>
      </div>
      <div className={`rounded-2xl p-3 ${tones[tone]}`}>{icon}</div>
    </div>
  );
}

function ExogRow({
  icon,
  title,
  subtitle,
  value,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl bg-slate-50 p-3">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-xs font-bold text-slate-800">{title}</p>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
      </div>
      <span className="text-xs font-bold text-slate-700">{value}</span>
    </div>
  );
}
