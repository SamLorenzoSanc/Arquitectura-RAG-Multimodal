


import DashboardLayout from "@/components/DashboardLayout";
import DashboardStats from "@/components/DashboardStats";
import UploadDocument from "@/components/UploadDocument";
import RecentDocuments from "@/components/RecentDocument";
import ProcessingJobs from "@/components/ProcessingJobs";
import RecentChats from "@/components/RecentChats";
import KnowledgeBases from "@/components/KnowledgeBases";

export default function Dashboard() {

    return (

        <DashboardLayout>
            <DashboardStats />
            <div className="grid grid-cols-12 gap-6 mt-6">

                <div className="col-span-7 space-y-6">
                    <UploadDocument />
                    <RecentDocuments />
                    <ProcessingJobs />
                </div>

                <div className="col-span-5 space-y-6">
                    <RecentChats />
                    <KnowledgeBases />
                </div>

            </div>
        </DashboardLayout>

    );

}