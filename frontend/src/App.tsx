import { Navbar, Footer } from './components';
import LandingPage from './pages/LandingPage';

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <LandingPage />
      </main>
      <Footer />
    </>
  );
}
