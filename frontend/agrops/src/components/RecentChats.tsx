import { MessageSquare } from "lucide-react";
import { useTranslation } from "@/i18n/I18nProvider";

export default function RecentChats() {
  const { t } = useTranslation();

  const chats = [
    t("dashboardWidgets.sampleChat1"),
    t("dashboardWidgets.sampleChat2"),
    t("dashboardWidgets.sampleChat3"),
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h2 className="font-semibold text-xl mb-4">
        {t("dashboardWidgets.recentChats")}
      </h2>
      <div className="space-y-3">
        {chats.map((chat) => (
          <div
            key={chat}
            className="flex gap-3 items-center p-3 rounded-lg hover:bg-gray-50"
          >
            <MessageSquare className="text-green-600" />
            {chat}
          </div>
        ))}
      </div>
    </div>
  );
}
