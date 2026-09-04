import { JobDashboard } from "@/components/dashboard/JobDashboard";

interface JobPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;
  return <JobDashboard jobId={id} />;
}
