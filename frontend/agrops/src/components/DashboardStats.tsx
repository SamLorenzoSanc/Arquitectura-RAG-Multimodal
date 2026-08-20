import { Database, FileText, MessageSquare, Cpu } from "lucide-react";
import { useTranslation } from "@/i18n/I18nProvider";

export default function DashboardStats() {
  const { t } = useTranslation();

  const stats = [
    {
      title: t("dashboardWidgets.documents"),
      value: 128,
      icon: FileText,
      color: "text-green-600",
    },
    {
      title: t("dashboardWidgets.knowledgeBases"),
      value: 5,
      icon: Database,
      color: "text-blue-600",
    },
    {
      title: t("dashboardWidgets.conversations"),
      value: 342,
      icon: MessageSquare,
      color: "text-orange-500",
    },
    {
      title: t("dashboardWidgets.processing"),
      value: 8,
      icon: Cpu,
      color: "text-purple-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
      {stats.map((item) => {
        const Icon = item.icon;
        return (
          <div
            key={item.title}
            className="bg-white rounded-xl shadow-sm border p-6"
          >
            <div className="flex justify-between items-center">
              <div>
                <p className="text-gray-500 text-sm">{item.title}</p>
                <h2 className="text-3xl font-bold mt-2">{item.value}</h2>
              </div>
              <Icon className={`${item.color}`} size={32} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
