import DashboardStats from "@/components/DashboardStats";
import RecentDocuments from "@/components/RecentDocument";
import RecentChats from "@/components/RecentChats";
import KnowledgeBases from "@/components/KnowledgeBases";

export default function DashboardOverview() {
    return (
        <div className="w-full overflow-hidden pb-4"> 
            <DashboardStats />
            
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">

                <div className="lg:col-span-7 space-y-6 min-w-0">
                    <RecentDocuments />
                </div>

                <div className="lg:col-span-5 space-y-6 min-w-0">
                    <RecentChats />
                    <KnowledgeBases />
                </div>
                
            </div>
        </div>
    );
}