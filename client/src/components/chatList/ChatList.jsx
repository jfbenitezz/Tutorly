import { Link } from "react-router-dom";
import "./chatList.css";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const ChatList = () => {
  const queryClient = useQueryClient();

  const { isPending, error, data } = useQuery({
    queryKey: ["userChats"],
    queryFn: () =>
      fetch(`http://localhost:3000/api/userchats`, {
        credentials: "include",
      }).then((res) => res.json()),
  });
  const deleteMutation = useMutation({
    mutationFn: (id) =>
      fetch(`http://localhost:3000/api/userchats/${id}`, {
        method: "DELETE",
        credentials: "include",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userChats"] });
    },
  });

  const handleDelete = (e, id) => {
    e.preventDefault(); // evita que el Link redirija
    if (confirm("¿Estás seguro de que quieres eliminar este chat?")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="chatList">
      <span className="title">DASHBOARD</span>
      <Link to="/dashboard">Crea un chat</Link>
      <Link to="/file-system">Sube las clases</Link>
      <Link to="/transcript-player">Transcripciones</Link> 
      <Link to="/study-guide-viewer">Guias de estudio</Link> 
      <Link to="/">Explora Tutorly</Link>
      <Link to="/">Contacto</Link>
      <hr />
      <span className="title">CHATS RECIENTES</span>
      <div className="list">
        {isPending
          ? "Cargando..."
          : error
          ? "¡Ocurrió un error!"
          : data?.map((chat) => (
            <div className="chatItem" key={chat._id}>
              <Link to={`/dashboard/chats/${chat._id}`}>
                {chat.title}
              </Link>
              <button
                className="deleteBtn"
                onClick={(e) => handleDelete(e, chat._id)}
              >
                <img src="/trash.png" alt="Eliminar" width="20" />
              </button>
            </div>
          ))
          }
      </div>
      <hr />
      <div className="upgrade">
        <img src="/logo.png" alt="" />
      </div>
    </div>
  );
};

export default ChatList;
