const panel = document.querySelector("[data-pedidos-url]");
const resumen = document.getElementById("resumen-pedidos");
const lista = document.getElementById("folios-pedidos");

async function actualizarPedidos() {
    try {
        const respuesta = await fetch(panel.dataset.pedidosUrl, { cache: "no-store" });
        if (respuesta.redirected || respuesta.status === 403) {
            resumen.textContent = "Vuelve a iniciar sesión con una cuenta autorizada.";
            lista.replaceChildren();
            return;
        }
        if (!respuesta.ok) {
            throw new Error("No se pudo consultar pedidos.");
        }
        const { total, folios } = await respuesta.json();
        const mensaje = total === 1 ? "1 pedido recibido" : `${total} pedidos recibidos`;
        if (resumen.textContent !== mensaje) {
            resumen.textContent = mensaje;
        }
        if (JSON.stringify(folios) !== JSON.stringify([...lista.children].map(item => item.textContent))) {
            lista.replaceChildren(...folios.map(folio => {
                const item = document.createElement("li");
                item.className = "list-group-item";
                item.textContent = folio;
                return item;
            }));
        }
    } catch {
        resumen.textContent = "No se pudo actualizar la lista de pedidos.";
        lista.replaceChildren();
    }
    window.setTimeout(actualizarPedidos, 15000);
}

actualizarPedidos();
