import Workspace from "@/components/Workspace";

export default async function Page({ params }: { params: Promise<{ groupId: string }> }) {
  const { groupId } = await params;
  return <Workspace groupId={Number(groupId)} />;
}
