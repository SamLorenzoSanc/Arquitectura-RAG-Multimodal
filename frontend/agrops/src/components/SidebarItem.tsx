import { Link } from "react-router-dom";

import type { LucideIcon } from "lucide-react";

interface Props {
    icon: LucideIcon;
    label: string;
    to: string;
}

export default function SidebarItem({
    icon: Icon,
    label,
    to
}: Props) {
    return (
        <Link
            to={to}
            className="flex items-center gap-3 rounded-lg px-4 py-3 text-slate-700 transition hover:bg-green-100 hover:text-green-700"
        >
            <Icon size={20} />
            <span>{label}</span>
        </Link>

    );

}