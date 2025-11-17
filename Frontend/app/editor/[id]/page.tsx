import EditorClient from "./EditorClient";

export default async function EditorPage({ params }) {
  const { id } = await params;
    return <EditorClient id={id} />;
}
