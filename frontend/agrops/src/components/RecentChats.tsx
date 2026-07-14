import { MessageSquare } from "lucide-react";

const chats = [

    "¿Qué ayudas PAC existen?",

    "Cultivo de aguacate",

    "Subvención POSEI"

];

export default function RecentChats() {

    return (

        <div className="bg-white rounded-xl shadow-sm border p-6">

            <h2 className="font-semibold text-xl mb-4">

                Conversaciones recientes

            </h2>

            <div className="space-y-3">

                {chats.map((chat) => (

                    <div
                        key={chat}
                        className="flex gap-3 items-center p-3 rounded-lg hover:bg-gray-50"
                    >

                        <MessageSquare
                            className="text-green-600"
                        />

                        {chat}

                    </div>

                ))}

            </div>

        </div>

    );

}