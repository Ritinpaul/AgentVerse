import { redirect } from "next/navigation";

// /landing now redirects to / (the new landing page route)
export default function LandingRedirectPage() {
  redirect("/");
}
