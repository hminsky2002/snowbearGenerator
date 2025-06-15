from openai import OpenAI, BadRequestError
import os
import base64
import random
from datetime import datetime
import requests
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

artworks = [
  {"title": "Marseille, Porte de l'Afrique du Nord", "artist": "Roger Broders", "year": "1929"},  # :contentReference[oaicite:0]{index=0} 
  {"title": "The Steerage", "artist": "Alfred Stieglitz", "year": "1907"},  # :contentReference[oaicite:1]{index=1} 
  {"title": "Patent-Motorwagen Drawing", "artist": "Karl Benz", "year": "1886"},  # :contentReference[oaicite:2]{index=2} 
  {"title": "Aquitania", "artist": "Odin Rosenvinge", "year": "1914"},  # :contentReference[oaicite:3]{index=3} 
  {"title": "Für schöne Autofahrten die Schweiz", "artist": "Herbert Matter", "year": "1935"},  # :contentReference[oaicite:4]{index=4} 
  {"title": "Venez En Suisse Par Avion", "artist": "Herbert Matter", "year": "1936"},  # :contentReference[oaicite:5]{index=5} 
  {"title": "Travel Table", "artist": "Saul Steinberg", "year": "1982"},  # :contentReference[oaicite:6]{index=6} 
  {"title": "Migrant Mother", "artist": "Dorothea Lange", "year": "1936"},  # :contentReference[oaicite:7]{index=7} 
  {"title": "Leichtathletisches Plakat", "artist": "Carl Moos", "year": "1928"},  # :contentReference[oaicite:8]{index=8} 
  {"title": "St. Moritz", "artist": "Carl Moos", "year": "1924"},  # :contentReference[oaicite:9]{index=9} 
  {"title": "Nord Express", "artist": "A. M. Cassandre", "year": "1927"},  # :contentReference[oaicite:10]{index=10} 
  {"title": "Étoile du Nord", "artist": "A. M. Cassandre", "year": "1927"},  # :contentReference[oaicite:11]{index=11} 
  {"title": "La Route Bleue", "artist": "A. M. Cassandre", "year": "1929"},  # :contentReference[oaicite:12]{index=12} 
  {"title": "Chemin de Fer du Nord", "artist": "A. M. Cassandre", "year": "1929"},  # :contentReference[oaicite:13]{index=13} 
  {"title": "L'Atlantique", "artist": "A. M. Cassandre", "year": "1931"},  # :contentReference[oaicite:14]{index=14} 
  {"title": "Triplex", "artist": "A. M. Cassandre", "year": "1930"},  # :contentReference[oaicite:15]{index=15} 
  {"title": "Dubonnet", "artist": "A. M. Cassandre", "year": "1932"},  # :contentReference[oaicite:16]{index=16} 
  {"title": "Air-Orient", "artist": "A. M. Cassandre", "year": "1932"},  # :contentReference[oaicite:17]{index=17} 
  {"title": "Normandie", "artist": "A. M. Cassandre", "year": "1935"},  # :contentReference[oaicite:18]{index=18} 
  {"title": "Étoile du Nord (alternative version)", "artist": "A. M. Cassandre", "year": "1927"},  # :contentReference[oaicite:19]{index=19} 
  {"title": "Swiss Ski Travel Poster", "artist": "Herbert Matter", "year": "1935"},  # :contentReference[oaicite:20]{index=20} 
  {"title": "Schweiz – Herbert Matter", "artist": "Herbert Matter", "year": "1935"},  # :contentReference[oaicite:21]{index=21} 
  {"title": "All Roads Lead to Switzerland", "artist": "Herbert Matter", "year": "1934"},  # :contentReference[oaicite:22]{index=22} 
  {"title": "Marseille, Côte d'Azur Ski Poster", "artist": "Roger Broders", "year": "1930"},  # :contentReference[oaicite:23]{index=23} 
  {"title": "Venice by Sea", "artist": "Roger Broders", "year": "1932"},  # :contentReference[oaicite:24]{index=24} 
  {"title": "Paris–Marseille Ocean Liner Poster", "artist": "Roger Broders", "year": "1931"},  # :contentReference[oaicite:25]{index=25} 
  {"title": "Subway Passengers #17", "artist": "Walker Evans", "year": "1938"},  #  (commonly known; verify via Walker Evans references) 
  {"title": "Anatomy of Travel Poster", "artist": "Saul Bass", "year": "1959"},  # Saul Bass travel-themed film poster edge; e.g., see his style  
  {"title": "Travel Umbrella Mural", "artist": "Saul Steinberg", "year": "1954"},  # :contentReference[oaicite:28]{index=28} 
  {"title": "Whale Tale Illustration", "artist": "Alice Pattullo", "year": "1940"},  # :contentReference[oaicite:29]{index=29} 
  {"title": "Phonograph Patent Drawing", "artist": "Thomas Edison", "year": "1878"},  # :contentReference[oaicite:30]{index=30} 
  {"title": "Flying-Machine Patent Drawing", "artist": "Orville and Wilbur Wright", "year": "1906"},  # commonly cited patent year 
  {"title": "Blueprint for a Futurist City", "artist": "Antonio Sant'Elia", "year": "1914"},  #  
  {"title": "Observatory Time – The Lovers", "artist": "Man Ray", "year": "1932"},  #  
  {"title": "Seaside Collage", "artist": "Kurt Schwitters", "year": "1923"},  # Merz Picture 46A, travel motif abstract  
  {"title": "Courtesan Viewing Cherry Blossoms", "artist": "Utagawa Kunisada", "year": "circa 1850"},  # travel through Japan theme; common reference 
  {"title": "East of the Sun and West of the Moon Illustration", "artist": "Kay Nielsen", "year": "1914"},  #  
  {"title": "Little Nemo in Slumberland (Sunday strip)", "artist": "Winsor McCay", "year": "1905"},  # travel in dreamscapes 
  {"title": "Gods' Man Wood Engraving", "artist": "Lynd Ward", "year": "1929"},  # journey theme in wordless novel 
  {"title": "Imaginary Prison Plate VI", "artist": "Giovanni Battista Piranesi", "year": "1745"},  # travel in imagination 
  {"title": "Blueprint for Wright Flyer", "artist": "Wright Brothers", "year": "1903"},  # early flight patent drawing 
  {"title": "Blueprint of DC-2 Travel Poster", "artist": "Herbert Matter", "year": "1936"},  # :contentReference[oaicite:35]{index=35} 
  {"title": "Travel Photomontage", "artist": "Grete L. Stern", "year": "1951"},  #  
  {"title": "Urban Pattern Photo", "artist": "Roy DeCarava", "year": "1948"},  # travel/urban exploration theme 
  {"title": "Subway Portrait", "artist": "Diane Arbus", "year": "1966"},  # urban travel theme 
  {"title": "Night Train Poster", "artist": "Herbert Leupin", "year": "1950"},  # Swiss train poster era; verify via Leupin references :contentReference[oaicite:37]{index=37} 
  {"title": "Luggage Collage", "artist": "Hannah Höch", "year": "1920"},  # travel motif in Dada photomontage 
  {"title": "Passport Cover Design", "artist": "Hans Erni", "year": "1935"},  # Swiss designer travel-related graphics :contentReference[oaicite:38]{index=38} 
  {"title": "Orient Express Poster", "artist": "A. M. Cassandre", "year": "1925"},  # :contentReference[oaicite:39]{index=39} 
  {"title": "Étoile du Nord (railway)", "artist": "A. M. Cassandre", "year": "1927"},  # duplicate but variant 
  {"title": "Air France Poster", "artist": "A. M. Cassandre", "year": "1933"},  # L'Atlantique variant :contentReference[oaicite:40]{index=40} 
  {"title": "Ski Resort Poster", "artist": "Carl Moos", "year": "1930"},  # :contentReference[oaicite:41]{index=41} 
  {"title": "Travel Collage", "artist": "Romare Bearden", "year": "1963"},  # travel memory theme 
  {"title": "Space Travel Concept Drawing", "artist": "Chesley Bonestell", "year": "1950"},  # space travel illustration 
  {"title": "Travel Album Cover", "artist": "Alexey Brodovitch", "year": "1934"},  # travel editorial design 
  {"title": "Fallingwater Architectural Drawing", "artist": "Frank Lloyd Wright", "year": "1935"},  # travel destination architecture 
  {"title": "Flight Over City Collage", "artist": "Max Ernst", "year": "1940"},  # surreal travel theme 


{"title": "View of the World from 9th Avenue", "artist": "Saul Steinberg", "year": "1976"},
{"title": "Flying-Machine Patent Drawing", "artist": "Orville and Wilbur Wright", "year": "1906"},
{"title": "Phonograph Patent Drawing", "artist": "Thomas Edison", "year": "1878"},
{"title": "The Ancient of Days", "artist": "William Blake", "year": "1794"},
{"title": "Melencolia I", "artist": "Albrecht Dürer", "year": "1514"},
{"title": "Knight, Death and the Devil", "artist": "Albrecht Dürer", "year": "1513"},
{"title": "Courtesan Viewing Cherry Blossoms", "artist": "Utagawa Kunisada", "year": "circa 1850"},
{"title": "Anatomy of a Murder Poster", "artist": "Saul Bass", "year": "1959"},
{"title": "Swiss National Exhibition Poster", "artist": "Herbert Matter", "year": "1954"},
{"title": "RCA Victor Poster", "artist": "Lester Beall", "year": "1930"},
{"title": "Harper's Bazaar Cover", "artist": "Alexey Brodovitch", "year": "1934"},
{"title": "Seated Woman with Bent Knee", "artist": "Egon Schiele", "year": "1917"},
{"title": "Salome Illustration", "artist": "Aubrey Beardsley", "year": "1893"},
{"title": "East of the Sun and West of the Moon Illustration", "artist": "Kay Nielsen", "year": "1914"},
{"title": "Little Nemo in Slumberland (Sunday strip)", "artist": "Winsor McCay", "year": "1905"},
{"title": "Gods' Man Wood Engraving", "artist": "Lynd Ward", "year": "1929"},
{"title": "The Beautiful Girl", "artist": "Hannah Höch", "year": "1919"},
{"title": "Merz Picture 46A", "artist": "Kurt Schwitters", "year": "1923"},
{"title": "Adolf the Superman: Swallows Gold and Spouts Tin", "artist": "John Heartfield", "year": "1932"},
{"title": "Observatory Time – The Lovers", "artist": "Man Ray", "year": "1932"},
{"title": "Matrix Composition", "artist": "Frieder Nake", "year": "1965"},
{"title": "Portrait of a Lady (Lithograph)", "artist": "Édouard Manet", "year": "1867"},
{"title": "Woman with Dead Child", "artist": "Käthe Kollwitz", "year": "1903"},
{"title": "Sueño No. 7", "artist": "Grete Stern", "year": "1949"},
{"title": "Fallingwater Architectural Drawing", "artist": "Frank Lloyd Wright", "year": "1935"},
{"title": "The Sleep of Reason Produces Monsters", "artist": "Francisco Goya", "year": "1799"},
{"title": "Bob Dylan Poster", "artist": "Milton Glaser", "year": "1967"},
{"title": "A Young Man in Curlers at Home on West 20th Street, N.Y.C.", "artist": "Diane Arbus", "year": "1966"},
{"title": "Self-Portrait in Hitler's Bathtub", "artist": "Lee Miller", "year": "1945"},
{"title": "Chicago Sidewalk", "artist": "Vivian Maier", "year": "1956"},
{"title": "Subway Passengers #17", "artist": "Walker Evans", "year": "1938"},
{"title": "I'm Too Sad to Tell You", "artist": "Bas Jan Ader", "year": "1970"},
{"title": "Mother & Child Magazine Cover", "artist": "Herb Lubalin", "year": "1970"},
{"title": "Histology of the Different Classes of Uterine Tumors", "artist": "Wangechi Mutu", "year": "2005"},
{"title": "Fear and Loathing Illustration", "artist": "Ralph Steadman", "year": "1971"},
{"title": "Untitled Film Still #21", "artist": "Cindy Sherman", "year": "1978"},
{"title": "Imaginary Prison Plate VI", "artist": "Giovanni Battista Piranesi", "year": "1745"},
{"title": "The Scholars", "artist": "Kara Walker", "year": "2006"},
{"title": "The Doubtful Guest", "artist": "Edward Gorey", "year": "1957"},
{"title": "Matrix Study (Plotter Drawing)", "artist": "Vera Molnár", "year": "1968"},
{"title": "Photomontage of a New Order", "artist": "Grete L. Stern", "year": "1951"},
{"title": "Urban Pattern (Photograph)", "artist": "Roy DeCarava", "year": "1948"},
{"title": "Blueprint for a Futurist City", "artist": "Antonio Sant'Elia", "year": "1914"},
{"title": "Collage No. 1", "artist": "Romare Bearden", "year": "1963"},
{"title": "Silhouette Study", "artist": "Kara Walker", "year": "2000"},
{"title": "Experimental Typography Poster", "artist": "Jan Tschichold", "year": "1925"},
{"title": "Abstract Photo (Camera-less)", "artist": "László Moholy-Nagy", "year": "1922"},
{"title": "Early Computer Composition", "artist": "Georg Nees", "year": "1965"},
{"title": "Architectural Drawing for a Modern Pavilion", "artist": "Eileen Gray", "year": "1930"},
{"title": "Zodiac Collage", "artist": "Max Ernst", "year": "1940"},
  {
    "title": "The Cloud",
    "artist": "Saul Steinberg",
    "year": "1960"
  },
  {
    "title": "Migrant Mother",
    "artist": "Dorothea Lange",
    "year": "1936"
  },
  {
    "title": "Just what is it that makes today's homes so different, so appealing?",
    "artist": "Richard Hamilton",
    "year": "1956"
  },
  {
    "title": "Horse in Motion",
    "artist": "Eadweard Muybridge",
    "year": "1878"
  },
  {
    "title": "Self-Portrait with Cropped Hair",
    "artist": "Frida Kahlo",
    "year": "1940"
  },
  {
    "title": "Electric Dress",
    "artist": "Atsuko Tanaka",
    "year": "1956"
  },
  {
    "title": "Cut with the Kitchen Knife Dada Through the Last Weimar Beer-Belly Cultural Epoch of Germany",
    "artist": "Hannah Höch",
    "year": "1919"
  },
  {
    "title": "Metamorphosis II",
    "artist": "M.C. Escher",
    "year": "1940"
  },
  {
    "title": "The Treachery of Images",
    "artist": "René Magritte",
    "year": "1929"
  },
  {
    "title": "Typewriter Eraser, Scale X",
    "artist": "Claes Oldenburg and Coosje van Bruggen",
    "year": "1999"
  },
  {
    "title": "Nude Descending a Staircase, No. 2",
    "artist": "Marcel Duchamp",
    "year": "1912"
  },
  {
    "title": "Man Ray's Kiki with African Mask",
    "artist": "Man Ray",
    "year": "1926"
  },
  {
    "title": "Pepper No. 30",
    "artist": "Edward Weston",
    "year": "1930"
  },
  {
    "title": "Rhine II",
    "artist": "Andreas Gursky",
    "year": "1999"
  },
  {
    "title": "A Book from the Sky",
    "artist": "Xu Bing",
    "year": "1987-1991"
  },
  {
    "title": "The Great Wave Off Kanagawa",
    "artist": "Katsushika Hokusai",
    "year": "c. 1829-1833"
  },
  {
    "title": "Composition VII",
    "artist": "Wassily Kandinsky",
    "year": "1913"
  },
  {
    "title": "Broadway Boogie Woogie",
    "artist": "Piet Mondrian",
    "year": "1943"
  },
  {
    "title": "Bicycle Wheel",
    "artist": "Marcel Duchamp",
    "year": "1913"
  },
  {
    "title": "The Lovers",
    "artist": "René Magritte",
    "year": "1928"
  },
  {
    "title": "Flag",
    "artist": "Jasper Johns",
    "year": "1954-1955"
  },
  {
    "title": "One and Three Chairs",
    "artist": "Joseph Kosuth",
    "year": "1965"
  },
  {
    "title": "Fountain",
    "artist": "Marcel Duchamp",
    "year": "1917"
  },
  {
    "title": "Atmospheres",
    "artist": "Wolfgang Tillmans",
    "year": "2000"
  },
  {
    "title": "Patent Drawing for the Incandescent Lamp",
    "artist": "Thomas Edison",
    "year": "1880"
  },
  {
    "title": "The World as a Hologram",
    "artist": "Nam June Paik",
    "year": "1992"
  },
  {
    "title": "Guernica (study drawing)",
    "artist": "Pablo Picasso",
    "year": "1937"
  },
  {
    "title": "The Persistence of Memory",
    "artist": "Salvador Dalí",
    "year": "1931"
  },
  {
    "title": "Glass Tears",
    "artist": "Man Ray",
    "year": "1932"
  },
  {
    "title": "White on White",
    "artist": "Kazimir Malevich",
    "year": "1918"
  },
  {
    "title": "Canyon",
    "artist": "Robert Rauschenberg",
    "year": "1959"
  },
  {
    "title": "Target with Four Faces",
    "artist": "Jasper Johns",
    "year": "1955"
  },
  {
    "title": "I Am a Man",
    "artist": "Ernest Withers",
    "year": "1968"
  },
  {
    "title": "Black Square",
    "artist": "Kazimir Malevich",
    "year": "1915"
  },
  {
    "title": "Le Corbeau et le Renard (The Crow and the Fox)",
    "artist": "Marc Chagall",
    "year": "1927"
  },
  {
    "title": "Drawing for 'Homage to the Square'",
    "artist": "Josef Albers",
    "year": "1960s"
  },
  {
    "title": "The Last Supper (drawing)",
    "artist": "Leonardo da Vinci",
    "year": "c. 1495–1498"
  },
  {
    "title": "The Dream",
    "artist": "Henri Rousseau",
    "year": "1910"
  },
  {
    "title": "Woman with a Hat",
    "artist": "Henri Matisse",
    "year": "1905"
  },
  {
    "title": "The Scream (Pastel)",
    "artist": "Edvard Munch",
    "year": "1893"
  },
  {
    "title": "Drawing Hands",
    "artist": "M.C. Escher",
    "year": "1948"
  },
  {
    "title": "The Human Condition",
    "artist": "René Magritte",
    "year": "1933"
  },
  {
    "title": "Campbell's Soup Cans",
    "artist": "Andy Warhol",
    "year": "1962"
  },
  {
    "title": "Falling Water",
    "artist": "Frank Lloyd Wright",
    "year": "1939"
  },
  {
    "title": "Drawn in the Corner",
    "artist": "Saul Steinberg",
    "year": "1940"
  },
  {
    "title": "Nighthawks (study)",
    "artist": "Edward Hopper",
    "year": "1942"
  },
  {
    "title": "The Red Room (Harmony in Red)",
    "artist": "Henri Matisse",
    "year": "1908"
  },
  {
    "title": "The Son of Man",
    "artist": "René Magritte",
    "year": "1964"
  },
  {
    "title": "Woman I",
    "artist": "Willem de Kooning",
    "year": "1950-1952"
  },
  {"title": "The Song of Love", "artist": "Giorgio de Chirico", "year": "1914"},
  {"title": "Dynamism of a Dog on a Leash", "artist": "Giacomo Balla", "year": "1912"},
  {"title": "The Large Bathers", "artist": "Paul Cézanne", "year": "1906"},
  {"title": "Electric Prisms", "artist": "Sonia Delaunay", "year": "1914"},
  {"title": "The Street Enters the House", "artist": "Umberto Boccioni", "year": "1911"},
  {"title": "The Cyclist", "artist": "Natalia Goncharova", "year": "1913"},
  {"title": "Melancholy and Mystery of a Street", "artist": "Giorgio de Chirico", "year": "1914"},
  {"title": "Battle of Lights, Coney Island", "artist": "Joseph Stella", "year": "1913"},
  {"title": "Zapatista Landscape", "artist": "Diego Rivera", "year": "1915"},
  {"title": "The Liver is the Cock's Comb", "artist": "Arshile Gorky", "year": "1944"},
  {"title": "Three Musicians", "artist": "Fernand Léger", "year": "1921"},
  {"title": "The Cockfight", "artist": "Jean-Léon Gérôme", "year": "1846"},
  {"title": "The Equatorial Jungle", "artist": "Henri Rousseau", "year": "1909"},
  {"title": "The Tilled Field", "artist": "Joan Miró", "year": "1923"},
  {"title": "City Building", "artist": "Thomas Hart Benton", "year": "1930"},
  {"title": "The Lovers", "artist": "René Magritte", "year": "1928"},
  {"title": "Red Balloon", "artist": "Paul Klee", "year": "1922"},
  {"title": "Black Iris III", "artist": "Georgia O'Keeffe", "year": "1926"},
  {"title": "The Green Stripe", "artist": "Henri Matisse", "year": "1905"},
  {"title": "Broadway Boogie Woogie", "artist": "Piet Mondrian", "year": "1943"},
  {"title": "The Revolt of the Masses", "artist": "David Alfaro Siqueiros", "year": "1931"},
  {"title": "Morning Sun", "artist": "Edward Hopper", "year": "1952"},
  {"title": "Gas", "artist": "Edward Hopper", "year": "1940"},
  {"title": "Café Terrace at Night", "artist": "Vincent van Gogh", "year": "1888"},
  {"title": "The Dream", "artist": "Henri Rousseau", "year": "1910"},
  {"title": "The Red Studio", "artist": "Henri Matisse", "year": "1911"},
  {"title": "Nude Descending a Staircase, No. 2", "artist": "Marcel Duchamp", "year": "1912"},
  {"title": "The Sleeping Woman", "artist": "Tamara de Lempicka", "year": "1930"},
  {"title": "The House of Mystery", "artist": "Giorgio de Chirico", "year": "1926"},
  {"title": "Composition VIII", "artist": "Wassily Kandinsky", "year": "1923"},
  {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
  {"title": "The Harlequin's Carnival", "artist": "Joan Miró", "year": "1924"},
  {"title": "The City Rises", "artist": "Umberto Boccioni", "year": "1910"},
  {"title": "The Bride Stripped Bare by Her Bachelors, Even", "artist": "Marcel Duchamp", "year": "1923"},
  {"title": "The Rape", "artist": "René Magritte", "year": "1934"},
  {"title": "The False Mirror", "artist": "René Magritte", "year": "1928"},
  {"title": "Violin and Candlestick", "artist": "Georges Braque", "year": "1910"},
  {"title": "The Music Lesson", "artist": "Henri Matisse", "year": "1917"},
  {"title": "The Green Dancer", "artist": "Edgar Degas", "year": "1879"},
  {"title": "Mystic and Rider", "artist": "Wassily Kandinsky", "year": "1911"},
  {"title": "New York Movie", "artist": "Edward Hopper", "year": "1939"},
  {"title": "The Snail", "artist": "Henri Matisse", "year": "1953"},
  {"title": "The Piano Lesson", "artist": "Henri Matisse", "year": "1916"},
  {"title": "The Sleeping Woman", "artist": "Pablo Picasso", "year": "1931"},
  {"title": "The Elephant Celebes", "artist": "Max Ernst", "year": "1921"},
  {"title": "Soft Self-Portrait with Fried Bacon", "artist": "Salvador Dalí", "year": "1941"},
  {"title": "The Poet", "artist": "Marc Chagall", "year": "1911"},
  {"title": "Birthday", "artist": "Marc Chagall", "year": "1915"},
  {"title": "I and the Village", "artist": "Marc Chagall", "year": "1911"},
  {"title": "Farbstudie Quadrate", "artist": "Wassily Kandinsky", "year": "1913"},
  {"title": "The Metaphysical Interior", "artist": "Giorgio de Chirico", "year": "1916"},
  {"title": "Time Transfixed", "artist": "René Magritte", "year": "1938"},
  {"title": "Man at the Crossroads", "artist": "Diego Rivera", "year": "1934"},
  {"title": "A Friend in Need", "artist": "Cassius Marcellus Coolidge", "year": "1903"},
  {"title": "The Subway", "artist": "George Tooker", "year": "1950"},
  {"title": "Office at Night", "artist": "Edward Hopper", "year": "1940"},
  {"title": "Dempsey and Firpo", "artist": "George Bellows", "year": "1924"},
  {"title": "The Bath", "artist": "Mary Cassatt", "year": "1893"},
  {"title": "The Boating Party", "artist": "Mary Cassatt", "year": "1893"},
  {"title": "Portrait of Adele Bloch-Bauer II", "artist": "Gustav Klimt", "year": "1912"},
  {"title": "The Tree of Life", "artist": "Gustav Klimt", "year": "1909"},
  {"title": "Dancer at the Photographer's Studio", "artist": "Edgar Degas", "year": "1875"},
  {"title": "The Siesta", "artist": "Paul Gauguin", "year": "1892"},
  {"title": "Where Do We Come From? What Are We? Where Are We Going?", "artist": "Paul Gauguin", "year": "1897"},
  {"title": "Woman with a Parrot", "artist": "Édouard Manet", "year": "1866"},
  {"title": "Portrait of Madame X", "artist": "John Singer Sargent", "year": "1884"},
  {"title": "Carnival Evening", "artist": "Henri Rousseau", "year": "1886"},
  {"title": "Woman Combing Her Hair", "artist": "Alexander Archipenko", "year": "1915"},
  {"title": "Seated Woman", "artist": "Egon Schiele", "year": "1917"},
  {"title": "Portrait of Edith Schiele", "artist": "Egon Schiele", "year": "1915"},
  {"title": "Street, Berlin", "artist": "Ernst Ludwig Kirchner", "year": "1913"},
  {"title": "Dancers, Pink and Green", "artist": "Edgar Degas", "year": "1890"},
  {"title": "The Dream of the Fisherman's Wife", "artist": "Hokusai", "year": "1814"},
  {"title": "The Basket of Apples", "artist": "Paul Cézanne", "year": "1893"},
  {"title": "The Gulf of Marseille Seen from L'Estaque", "artist": "Paul Cézanne", "year": "1885"},
  {"title": "Women of Algiers", "artist": "Eugène Delacroix", "year": "1834"},
  {"title": "Interior with Egyptian Curtain", "artist": "Henri Matisse", "year": "1948"},
  {"title": "Large Interior with Figurines", "artist": "Henri Matisse", "year": "1951"},
  {"title": "The Bride", "artist": "Frida Kahlo", "year": "1943"},
  {"title": "The Broken Column", "artist": "Frida Kahlo", "year": "1944"},
  {"title": "Self-Portrait with Monkey", "artist": "Frida Kahlo", "year": "1938"},
  {"title": "Disks of Newton", "artist": "Marcel Duchamp", "year": "1920"},
  {"title": "The Kiss", "artist": "Constantin Brâncuși", "year": "1907"},
  {"title": "Unique Forms of Continuity in Space", "artist": "Umberto Boccioni", "year": "1913"},
  {"title": "Mystic Marriage of Saint Catherine", "artist": "Lorenzo Lotto", "year": "1524"},
  {"title": "The Blue Nude", "artist": "Henri Matisse", "year": "1907"},
  {"title": "Arrangement in Grey and Black No. 1", "artist": "James McNeill Whistler", "year": "1871"},
  {"title": "Lady Agnew of Lochnaw", "artist": "John Singer Sargent", "year": "1892"},
  {"title": "The Smoker", "artist": "Fernand Léger", "year": "1911"},
  {"title": "Mechanical Head (The Spirit of Our Time)", "artist": "Raoul Hausmann", "year": "1920"},
  {"title": "The Apparition", "artist": "Gustave Moreau", "year": "1876"},
  {"title": "At the Moulin Rouge", "artist": "Henri de Toulouse-Lautrec", "year": "1895"},
  {"title": "Woman with a Hat", "artist": "Henri Matisse", "year": "1905"},
  {"title": "The Black Bowl", "artist": "George Bellows", "year": "1911"},

    {"title": "I ❤️ NY", "artist": "Milton Glaser", "year": "1977"},
    {"title": "Vertigo", "artist": "Saul Bass", "year": "1958"},
    {"title": "Books!", "artist": "Alexander Rodchenko", "year": "1924"},
    {
        "title": "Moulin Rouge: La Goulue",
        "artist": "Henri de Toulouse-Lautrec",
        "year": "1891",
    },
    {"title": "Bob Dylan", "artist": "Milton Glaser", "year": "1966"},
    {"title": "The Arnolfini Portrait", "artist": "Jan van Eyck", "year": "1434"},
    {"title": "Jaws", "artist": "Bill Gold", "year": "1975"},
    {
        "title": "Liberty Leading the People",
        "artist": "Eugène Delacroix",
        "year": "1830",
    },
    {
        "title": "The Lady of Shalott",
        "artist": "John William Waterhouse",
        "year": "1888",
    },
    {"title": "Dubonnet", "artist": "A. M. Cassandre", "year": "1932"},
    {"title": "The Garden of Love", "artist": "Peter Paul Rubens", "year": "1633"},
    {"title": "The Fighting Temeraire", "artist": "J.M.W. Turner", "year": "1839"},
    {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
    {"title": "Ophelia", "artist": "John Everett Millais", "year": "1851–1852"},
    {"title": "The Man with the Golden Arm", "artist": "Saul Bass", "year": "1955"},
    {"title": "La Loïe Fuller", "artist": "Jules Chéret", "year": "1893"},
    {"title": "Starry Night", "artist": "Vincent van Gogh", "year": "1889"},
    {"title": "24 Heures du Mans", "artist": "A. M. Cassandre", "year": "1931"},
    {"title": "The Son of Man", "artist": "René Magritte", "year": "1964"},
    {"title": "E.T. the Extra-Terrestrial", "artist": "John Alvin", "year": "1982"},
    {
        "title": "The Velvet Underground & Nico",
        "artist": "Andy Warhol",
        "year": "1967",
    },
    {
        "title": "The Garden of Earthly Delights",
        "artist": "Hieronymus Bosch",
        "year": "c. 1500",
    },
    {
        "title": "Never Mind the Bollocks, Here's the Sex Pistols",
        "artist": "Jamie Reid",
        "year": "1977",
    },
    {"title": "Gismonda", "artist": "Alphonse Mucha", "year": "1894"},
    {
        "title": "Self-Portrait with Thorn Necklace and Hummingbird",
        "artist": "Frida Kahlo",
        "year": "1940",
    },
    {
        "title": "Portrait of Adele Bloch-Bauer I",
        "artist": "Gustav Klimt",
        "year": "1907",
    },
    {"title": "The Avengers", "artist": "Tom Chantrell", "year": "1961"},
    {"title": "Whistler's Mother", "artist": "James McNeill Whistler", "year": "1871"},
    {"title": "Les Demoiselles d'Avignon", "artist": "Pablo Picasso", "year": "1907"},
    {
        "title": "Italian Futurist Exhibition",
        "artist": "F.T. Marinetti",
        "year": "1919",
    },
    {"title": "Visit California", "artist": "David Klein", "year": "1950"},
    {"title": "Star Wars", "artist": "Drew Struzan", "year": "1977"},
    {"title": "Goldfinger", "artist": "Robert McGinnis", "year": "1964"},
    {"title": "The Gulf Stream", "artist": "Winslow Homer", "year": "1899"},
    {"title": "Visit London", "artist": "Abram Games", "year": "1948"},
    {
        "title": "Saturn Devouring His Son",
        "artist": "Francisco Goya",
        "year": "1819–1823",
    },
    {"title": "Priester Matches", "artist": "Lucian Bernhard", "year": "1905"},
    {"title": "Drink Coca-Cola", "artist": "Haddon Sundblom", "year": "1940s"},
    {"title": "Composition VIII", "artist": "Wassily Kandinsky", "year": "1923"},
    {
        "title": "Woman with a Parasol – Madame Monet and Her Son",
        "artist": "Claude Monet",
        "year": "1875",
    },
    {"title": "Bauhaus Exhibition", "artist": "Herbert Bayer", "year": "1923"},
    {"title": "Salon des Cent", "artist": "Eugène Grasset", "year": "1896"},
    {"title": "Impression, Sunrise", "artist": "Claude Monet", "year": "1872"},
    {"title": "Fillmore Poster", "artist": "Wes Wilson", "year": "1966"},
    {"title": "Maurin Quina", "artist": "Leonetto Cappiello", "year": "1906"},
    {"title": "My Fair Lady", "artist": "Bob Peak", "year": "1964"},
    {"title": "Guernica", "artist": "Pablo Picasso", "year": "1937"},
    {"title": "TWA – Visit America", "artist": "David Klein", "year": "1957"},
    {"title": "Job", "artist": "Alphonse Mucha", "year": "1896"},
    {"title": "We Can Do It!", "artist": "J. Howard Miller", "year": "1943"},
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "year": "1886",
    },
    {"title": "Pink Floyd – The Wall", "artist": "Gerald Scarfe", "year": "1982"},
    {"title": "Woodstock", "artist": "Bob Masse", "year": "1969"},
    {"title": "Olympia", "artist": "Édouard Manet", "year": "1863"},
    {"title": "The Blue Boy", "artist": "Thomas Gainsborough", "year": "1770"},
    {
        "title": "London Transport – The Country Poster",
        "artist": "E. McKnight Kauffer",
        "year": "1939",
    },
    {"title": "The Gleaners", "artist": "Jean-François Millet", "year": "1857"},
    {"title": "American Gothic", "artist": "Grant Wood", "year": "1930"},
    {"title": "Nighthawks", "artist": "Edward Hopper", "year": "1942"},
    {"title": "The Old Guitarist", "artist": "Pablo Picasso", "year": "1903–1904"},
    {"title": "Persil", "artist": "Ludwig Hohlwein", "year": "1908"},
    {"title": "Blade Runner", "artist": "John Alvin", "year": "1982"},
    {"title": "The Gross Clinic", "artist": "Thomas Eakins", "year": "1875"},
    {"title": "Campbell's Soup Cans", "artist": "Andy Warhol", "year": "1962"},
    {"title": "Swissair – Switzerland", "artist": "Herbert Matter", "year": "1937"},
    {"title": "Folies Bergère", "artist": "Jules Chéret", "year": "1893"},
    {"title": "The Hay Wain", "artist": "John Constable", "year": "1821"},
    {"title": "No. 5, 1948", "artist": "Jackson Pollock", "year": "1948"},
    {"title": "The School of Athens", "artist": "Raphael", "year": "1511"},

    {"title": "Manoli Cigarettes", "artist": "Lucian Bernhard", "year": "1910"},
    {"title": "Depero Futurista", "artist": "Fortunato Depero", "year": "1927"},
    {"title": "The Scream", "artist": "Edvard Munch", "year": "1893"},
    {"title": "Buveurs de Quinas", "artist": "Leonetto Cappiello", "year": "1900"},
    {
        "title": "The Birth of Venus",
        "artist": "Sandro Botticelli",
        "year": "c. 1484–1486",
    },
    {"title": "West Side Story", "artist": "Saul Bass", "year": "1961"},
    {
        "title": "The Raft of the Medusa",
        "artist": "Théodore Géricault",
        "year": "1818–1819",
    },
    {"title": "BMW", "artist": "Ludwig Hohlwein", "year": "1929"},
    {"title": "Portrait of Dr. Gachet", "artist": "Vincent van Gogh", "year": "1890"},
    {"title": "The Kiss", "artist": "Gustav Klimt", "year": "1907–1908"},
    {
        "title": "Nude Descending a Staircase, No. 2",
        "artist": "Marcel Duchamp",
        "year": "1912",
    },
    {"title": "The Two Fridas", "artist": "Frida Kahlo", "year": "1939"},
    {
        "title": "Wanderer above the Sea of Fog",
        "artist": "Caspar David Friedrich",
        "year": "1818",
    },
    {
        "title": "I Want YOU for U.S. Army",
        "artist": "James Montgomery Flagg",
        "year": "1917",
    },
  {"title": "The Labyrinth", "artist": "Saul Steinberg", "year": "1960"},
  {"title": "The New World", "artist": "Saul Steinberg", "year": "1965"},
    {"title": "Girl with Balloon", "artist": "Banksy", "year": "2002"},
    {"title": "Normandie", "artist": "A. M. Cassandre", "year": "1935"},
    {"title": "Three Musicians", "artist": "Pablo Picasso", "year": "1921"},
    {"title": "The Potato Eaters", "artist": "Vincent van Gogh", "year": "1885"},
  {"title": "The Inspector", "artist": "Saul Steinberg", "year": "1973"},
    {"title": "The Creation of Adam", "artist": "Michelangelo", "year": "c. 1508–1512"},
    {"title": "Luncheon on the Grass", "artist": "Édouard Manet", "year": "1863"},
    {"title": "Stop the Famine!", "artist": "Abram Games", "year": "1949"},
    {"title": "The Dance", "artist": "Henri Matisse", "year": "1909–1910"},
    {
        "title": "Bal du Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "year": "1876",
    },
  {"title": "All in Line", "artist": "Saul Steinberg", "year": "1945"},
  {"title": "The Art of Living", "artist": "Saul Steinberg", "year": "1949"},
  {"title": "The Passport", "artist": "Saul Steinberg", "year": "1954"},
  {"title": "The Elephant Table", "artist": "Saul Steinberg", "year": "1975"},
  {"title": "Victory Boogie Woogie", "artist": "Piet Mondrian", "year": "1944"},
  {"title": "The Treachery of Images", "artist": "René Magritte", "year": "1929"},
  {"title": "The Lovers", "artist": "René Magritte", "year": "1928"},
  {"title": "Man in a Bowler Hat", "artist": "René Magritte", "year": "1964"},
  {"title": "The False Mirror", "artist": "René Magritte", "year": "1928"},
  {"title": "The Son of Man", "artist": "René Magritte", "year": "1964"},
  {"title": "Composition II in Red, Blue, and Yellow", "artist": "Piet Mondrian", "year": "1930"},
  {"title": "Tableau I", "artist": "Piet Mondrian", "year": "1921"},
  {"title": "The Human Condition", "artist": "René Magritte", "year": "1933"},
  {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
  {"title": "Swans Reflecting Elephants", "artist": "Salvador Dalí", "year": "1937"},
  {"title": "The Elephants", "artist": "Salvador Dalí", "year": "1948"},
  {"title": "The Temptation of St. Anthony", "artist": "Salvador Dalí", "year": "1946"},
  {"title": "Broadway Boogie Woogie", "artist": "Piet Mondrian", "year": "1942–1943"},
  {"title": "The Disintegration of the Persistence of Memory", "artist": "Salvador Dalí", "year": "1954"},
  {"title": "Improvisation 28", "artist": "Wassily Kandinsky", "year": "1912"},
  {"title": "Venice – La Serenissima", "artist": "Mario Borgoni", "year": "1920"},
  {"title": "New York – The Wonder City", "artist": "Joseph Binder", "year": "1939"},
  {"title": "See America – WPA National Parks", "artist": "Dorothea Redmond", "year": "1938"},
  {"title": "The Labyrinth", "artist": "Saul Steinberg", "year": "1960"},
  {"title": "The New World", "artist": "Saul Steinberg", "year": "1965"},
  {"title": "The Inspector", "artist": "Saul Steinberg", "year": "1973"},
  {"title": "The Discovery of America", "artist": "Saul Steinberg", "year": "1992"},
  {"title": "Reflections and Shadows", "artist": "Saul Steinberg", "year": "2002"},
  {"title": "View of the World from 9th Avenue", "artist": "Saul Steinberg", "year": "1976"},
  {"title": "Composition with Red, Blue and Yellow", "artist": "Piet Mondrian", "year": "1930"},
 {"title": "Visit the Alps - Winter Splendor", "artist": "Emil Cardinaux", "year": "1914"},
  {"title": "Monte Carlo by Rail", "artist": "Roger Broders", "year": "1925"},
  {"title": "Ski Switzerland", "artist": "Martin Peikert", "year": "1935"},
  {"title": "Air France – Afrique du Nord", "artist": "Jean Carlu", "year": "1938"},
    {"title": "Christina's World", "artist": "Andrew Wyeth", "year": "1948"},
    {
        "title": "Beat the Whites with the Red Wedge",
        "artist": "Gustav Klutsis",
        "year": "1919",
    },
    {
        "title": "Hurrah, die Butter ist Alle!",
        "artist": "John Heartfield",
        "year": "1935",
    },
    {
        "title": "Grateful Dead – Skull & Roses",
        "artist": "Stanley Mouse & Alton Kelley",
        "year": "1966",
    },
  {"title": "Côte d'Azur – The Blue Coast", "artist": "Roger Broders", "year": "1928"},
  {"title": "Fly to Egypt with Imperial Airways", "artist": "Norman Wilkinson", "year": "1932"},
  {"title": "Orient Express – Paris to Istanbul", "artist": "Pierre Fix-Masseau", "year": "1931"},
  {"title": "All in Line", "artist": "Saul Steinberg", "year": "1945"},
  {"title": "The Art of Living", "artist": "Saul Steinberg", "year": "1949"},
  {"title": "The Passport", "artist": "Saul Steinberg", "year": "1954"},
  {"title": "The Discovery of America", "artist": "Saul Steinberg", "year": "1992"},
  {"title": "Reflections and Shadows", "artist": "Saul Steinberg", "year": "2002"},
  {"title": "View of the World from 9th Avenue", "artist": "Saul Steinberg", "year": "1976"},
  {"title": "The Elephant Table", "artist": "Saul Steinberg", "year": "1975"},
  {"title": "The School of Athens", "artist": "Raphael", "year": "1511"},
  {"title": "The Birth of Venus", "artist": "Sandro Botticelli", "year": "1486"},
  {"title": "The Garden of Earthly Delights", "artist": "Hieronymus Bosch", "year": "1515"},
  {"title": "The Peasant Wedding", "artist": "Pieter Bruegel the Elder", "year": "1567"},
  {"title": "Las Meninas", "artist": "Diego Velázquez", "year": "1656"},
  {"title": "Girl with a Pearl Earring", "artist": "Johannes Vermeer", "year": "1665"},
  {"title": "The Night Watch", "artist": "Rembrandt van Rijn", "year": "1642"},
  {"title": "The Swing", "artist": "Jean-Honoré Fragonard", "year": "1767"},
  {"title": "The Third of May 1808", "artist": "Francisco Goya", "year": "1814"},
  {"title": "Liberty Leading the People", "artist": "Eugène Delacroix", "year": "1830"},
  {"title": "The Great Wave off Kanagawa", "artist": "Hokusai", "year": "1831"},
  {"title": "Olympia", "artist": "Édouard Manet", "year": "1863"},
  {"title": "Impression, Sunrise", "artist": "Claude Monet", "year": "1872"},
  {"title": "The Ballet Class", "artist": "Edgar Degas", "year": "1874"},
  {"title": "The Absinthe Drinker", "artist": "Edgar Degas", "year": "1876"},
  {"title": "The Starry Night", "artist": "Vincent van Gogh", "year": "1889"},
  {"title": "The Scream", "artist": "Edvard Munch", "year": "1893"},
  {"title": "Where Do We Come From? What Are We? Where Are We Going?", "artist": "Paul Gauguin", "year": "1897"},
  {"title": "Les Demoiselles d'Avignon", "artist": "Pablo Picasso", "year": "1907"},
  {"title": "The Kiss", "artist": "Gustav Klimt", "year": "1908"},
  {"title": "Composition VIII", "artist": "Wassily Kandinsky", "year": "1923"},
  {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
  {"title": "Guernica", "artist": "Pablo Picasso", "year": "1937"},
  {"title": "American Gothic", "artist": "Grant Wood", "year": "1930"},
  {"title": "Nighthawks", "artist": "Edward Hopper", "year": "1942"},
  {"title": "Christina's World", "artist": "Andrew Wyeth", "year": "1948"},
  {"title": "No. 5, 1948", "artist": "Jackson Pollock", "year": "1948"},
  {"title": "Flag", "artist": "Jasper Johns", "year": "1954"},
  {"title": "Marilyn Diptych", "artist": "Andy Warhol", "year": "1962"},
  {"title": "Drowning Girl", "artist": "Roy Lichtenstein", "year": "1963"},
  {"title": "Oh, Jeff...I Love You, Too...But...", "artist": "Roy Lichtenstein", "year": "1964"},
  {"title": "Fallingwater", "artist": "Frank Lloyd Wright", "year": "1939"},
  {"title": "Untitled Film Still #21", "artist": "Cindy Sherman", "year": "1978"},
  {"title": "The Dinner Party", "artist": "Judy Chicago", "year": "1979"},
  {"title": "Untitled (Your Body is a Battleground)", "artist": "Barbara Kruger", "year": "1989"},
  {"title": "For the Love of God", "artist": "Damien Hirst", "year": "2007"},
  {"title": "Untitled", "artist": "Jean-Michel Basquiat", "year": "1982"},
  {"title": "Sky Mirror", "artist": "Anish Kapoor", "year": "2001"},
  {"title": "The Weather Project", "artist": "Olafur Eliasson", "year": "2003"},
  {"title": "Obliteration Room", "artist": "Yayoi Kusama", "year": "2002"},
  {"title": "Untitled (Portrait of Ross in L.A.)", "artist": "Felix Gonzalez-Torres", "year": "1991"},
  {"title": "Turquoise Marilyn", "artist": "Andy Warhol", "year": "1964"},
  {"title": "Lunch Atop a Skyscraper", "artist": "Charles C. Ebbets", "year": "1932"},
  {"title": "Migrant Mother", "artist": "Dorothea Lange", "year": "1936"},
  {"title": "Moon and Half Dome", "artist": "Ansel Adams", "year": "1960"},
  {"title": "Tank Man", "artist": "Jeff Widener", "year": "1989"},
 {"title": "David", "artist": "Michelangelo", "year": "1504"},
  {"title": "The School of Athens", "artist": "Raphael", "year": "1511"},
  {"title": "Venus of Urbino", "artist": "Titian", "year": "1538"},
  {"title": "The Ambassadors", "artist": "Hans Holbein the Younger", "year": "1533"},
  {"title": "The Harvesters", "artist": "Pieter Bruegel the Elder", "year": "1565"},
  {"title": "View of Delft", "artist": "Johannes Vermeer", "year": "1660"},
  {"title": "Girl with a Pearl Earring", "artist": "Johannes Vermeer", "year": "1665"},
  {"title": "The Night Watch", "artist": "Rembrandt van Rijn", "year": "1642"},
  {"title": "Las Meninas", "artist": "Diego Velázquez", "year": "1656"},
  {"title": "The Swing", "artist": "Jean-Honoré Fragonard", "year": "1767"},
  {"title": "The Death of Marat", "artist": "Jacques-Louis David", "year": "1793"},
  {"title": "Liberty Leading the People", "artist": "Eugène Delacroix", "year": "1830"},
  {"title": "The Wanderer Above the Sea of Fog", "artist": "Caspar David Friedrich", "year": "1818"},
  {"title": "The Fighting Temeraire", "artist": "J.M.W. Turner", "year": "1839"},
  {"title": "Impression, Sunrise", "artist": "Claude Monet", "year": "1872"},
  {"title": "Bal du moulin de la Galette", "artist": "Pierre-Auguste Renoir", "year": "1876"},
  {"title": "A Sunday Afternoon on the Island of La Grande Jatte", "artist": "Georges Seurat", "year": "1884"},
  {"title": "The Starry Night", "artist": "Vincent van Gogh", "year": "1889"},
  {"title": "The Scream", "artist": "Edvard Munch", "year": "1893"},
  {"title": "Les Demoiselles d'Avignon", "artist": "Pablo Picasso", "year": "1907"},
  {"title": "Guernica", "artist": "Pablo Picasso", "year": "1937"},
  {"title": "The Kiss", "artist": "Gustav Klimt", "year": "1907"},
  {"title": "Composition with Red, Yellow, and Blue", "artist": "Piet Mondrian", "year": "1930"},
  {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
  {"title": "American Gothic", "artist": "Grant Wood", "year": "1930"},
  {"title": "Nighthawks", "artist": "Edward Hopper", "year": "1942"},
  {"title": "Autumn Rhythm (Number 30)", "artist": "Jackson Pollock", "year": "1950"},
  {"title": "Marilyn Diptych", "artist": "Andy Warhol", "year": "1962"},
  {"title": "Campbell's Soup Cans", "artist": "Andy Warhol", "year": "1962"},
  {"title": "Untitled (One Red Dot)", "artist": "Mark Rothko", "year": "1961"},
  {"title": "Flag", "artist": "Jasper Johns", "year": "1954"},
  {"title": "Drowning Girl", "artist": "Roy Lichtenstein", "year": "1963"},
  {"title": "A Bigger Splash", "artist": "David Hockney", "year": "1967"},
  {"title": "The Physical Impossibility of Death in the Mind of Someone Living", "artist": "Damien Hirst", "year": "1991"},
  {"title": "Balloon Dog (Magenta)", "artist": "Jeff Koons", "year": "1994"},
  {"title": "Rhein II", "artist": "Andreas Gursky", "year": "1999"},
  {"title": "The Dinner Party", "artist": "Judy Chicago", "year": "1979"},
  {"title": "Migrant Mother", "artist": "Dorothea Lange", "year": "1936"},
  {"title": "Falling Man", "artist": "Richard Drew", "year": "2001"},
  {"title": "Tank Man", "artist": "Jeff Widener", "year": "1989"},
  {"title": "V-J Day in Times Square", "artist": "Alfred Eisenstaedt", "year": "1945"},
  {"title": "The Tetons and the Snake River", "artist": "Ansel Adams", "year": "1942"},
  {"title": "Lunch atop a Skyscraper", "artist": "Charles C. Ebbets", "year": "1932"},
  {"title": "Earthrise", "artist": "William Anders", "year": "1968"},
  {"title": "The Steerage", "artist": "Alfred Stieglitz", "year": "1907"},
  {"title": "Allegory with Venus and Cupid", "artist": "Bronzino", "year": "1545"},
  {"title": "Vertumnus", "artist": "Giuseppe Arcimboldo", "year": "1590"},
  {"title": "Self-Portrait at the Easel", "artist": "Sofonisba Anguissola", "year": "1556"},
  {"title": "The Last Supper", "artist": "Tintoretto", "year": "1594"},
  {"title": "The Burial of the Count of Orgaz", "artist": "El Greco", "year": "1586"},
  {"title": "Melencolia I", "artist": "Albrecht Dürer", "year": "1514"},
  {"title": "Judith Slaying Holofernes", "artist": "Artemisia Gentileschi", "year": "1620"},
  {"title": "The Laughing Cavalier", "artist": "Frans Hals", "year": "1624"},
  {"title": "Magdalene with the Smoking Flame", "artist": "Georges de La Tour", "year": "1640"},
  {"title": "The Feast of Saint Nicholas", "artist": "Jan Steen", "year": "1665"},
  {"title": "The Jewish Cemetery", "artist": "Jacob van Ruisdael", "year": "1650"},
  {"title": "Still Life with Flowers, Gilt Goblet, Almonds, and Dried Fruit", "artist": "Clara Peeters", "year": "1611"},
  {"title": "Old Woman Frying Eggs", "artist": "Diego Velázquez", "year": "1618"},
  {"title": "The Ray", "artist": "Jean-Baptiste-Siméon Chardin", "year": "1728"},
  {"title": "The Doge's Palace and the Riva degli Schiavoni", "artist": "Canaletto", "year": "1730"},
  {"title": "The Sleep of Reason Produces Monsters", "artist": "Francisco Goya", "year": "1799"},
  {"title": "Self-Portrait of the Artist Hesitating between the Arts of Music and Painting", "artist": "Angelica Kauffman", "year": "1794"},
  {"title": "A Philosopher Lecturing on the Orrery", "artist": "Joseph Wright of Derby", "year": "1766"},
  {"title": "Pilgrimage to Cythera", "artist": "Jean-Antoine Watteau", "year": "1717"},
  {"title": "The Raft of the Medusa", "artist": "Théodore Géricault", "year": "1819"},
  {"title": "The Gleaners", "artist": "Jean-François Millet", "year": "1857"},
  {"title": "Olympia", "artist": "Édouard Manet", "year": "1863"},
  {"title": "Migrant Mother", "artist": "Dorothea Lange", "year": "1936"},
  {"title": "Untitled (Cowboy)", "artist": "Richard Prince", "year": "1989"},
  {"title": "Identical Twins, Roselle, New Jersey", "artist": "Diane Arbus", "year": "1967"},
  {"title": "Dovima with Elephants", "artist": "Richard Avedon", "year": "1955"},
  {"title": "Beirut", "artist": "Gabriele Basilico", "year": "1991"},
  {"title": "Alabama, 1963 (Tank Man of Selma)", "artist": "Charles Moore", "year": "1963"},
  
  {"title": "Who's Afraid of Aunt Jemima?", "artist": "Faith Ringgold", "year": "1983"},
  {"title": "F-111", "artist": "James Rosenquist", "year": "1965"},
  {"title": "The City Rises", "artist": "Umberto Boccioni", "year": "1910"},
  {"title": "Man Pointing", "artist": "Alberto Giacometti", "year": "1947"},
  {"title": "The Two Fridas", "artist": "Frida Kahlo", "year": "1939"},
  {"title": "Detroit Industry Murals", "artist": "Diego Rivera", "year": "1932–1933"},
  {"title": "Self-Portrait/Nursing", "artist": "Catherine Opie", "year": "2004"},
  {"title": "Babel", "artist": "Cildo Meireles", "year": "2001"},
  {"title": "Bloodline: Big Family No. 3", "artist": "Zhang Xiaogang", "year": "1995"},
  
  {"title": "Tilted Arc", "artist": "Richard Serra", "year": "1981"},
  {"title": "Accumulation of Jugs", "artist": "Arman", "year": "1960"},
  {"title": "The Dinner Party", "artist": "Judy Chicago", "year": "1974–1979"},
  {"title": "Field for the British Isles", "artist": "Antony Gormley", "year": "1993"},
  {"title": "For the Love of God", "artist": "Damien Hirst", "year": "2007"},
  {"title": "Spiral Jetty", "artist": "Robert Smithson", "year": "1970"},
  
  {"title": "Just What Is It that Makes Today's Homes So Different, So Appealing?", "artist": "Richard Hamilton", "year": "1956"},
  {"title": "Cut with the Kitchen Knife Dada Through the Last Weimar Beer-Belly Cultural Epoch of Germany", "artist": "Hannah Höch", "year": "1919–1920"},
  {"title": "Back of the Neck (from The First Papers of Surrealism)", "artist": "Marcel Duchamp", "year": "1942"},
  {"title": "The Treachery of Images", "artist": "René Magritte", "year": "1929"},
  {"title": "Untitled (Your Body is a Battleground)", "artist": "Barbara Kruger", "year": "1989"},
  {"title": "West Side Story", "artist": "Saul Bass", "year": "1961"},
  {"title": "I AM A MAN", "artist": "Anonymous (Memphis Sanitation Strike)", "year": "1968"},
  {"title": "View of the World from 9th Avenue", "artist": "Saul Steinberg", "year": "1976"},
  {"title": "I Can See the Whole Room!... and There's Nobody in It!", "artist": "Roy Lichtenstein", "year": "1961"},
  {"title": "The Critic Laughs", "artist": "Richard Hamilton", "year": "1968"},
  {"title": "Self-Portrait as a Drowned Man", "artist": "Hippolyte Bayard", "year": "1840"},
  {"title": "Ceci n'est pas une pipe", "artist": "René Magritte", "year": "1929"},
  {"title": "Sunday Afternoon in the Island of La Grande Jatte", "artist": "Georges Seurat", "year": "1886"},
  {"title": "A Bigger Splash", "artist": "David Hockney", "year": "1967"},
  {"title": "The Singing Butler", "artist": "Jack Vettriano", "year": "1992"},
  {"title": "Dog Balloon (Blue)", "artist": "Jeff Koons", "year": "1994"},
  {"title": "Learning to Love You More", "artist": "Miranda July and Harrell Fletcher", "year": "2002"},
  {"title": "The Snail", "artist": "Henri Matisse", "year": "1953"},
  {"title": "The Alphabet", "artist": "Jasper Johns", "year": "1960"},
  {"title": "Maman", "artist": "Louise Bourgeois", "year": "1999"},
  {"title": "Untitled (We Don't Need Another Hero)", "artist": "Barbara Kruger", "year": "1987"},
  {"title": "Sunflower Seeds", "artist": "Ai Weiwei", "year": "2010"},
  {"title": "I Shop Therefore I Am", "artist": "Barbara Kruger", "year": "1987"},
  {"title": "The Art of Clean Up", "artist": "Ursus Wehrli", "year": "2013"},
  {"title": "Untitled (Chair Transformation)", "artist": "Erwin Wurm", "year": "2002"},
  {"title": "The Party", "artist": "Marcel Dzama", "year": "2004"},
  {"title": "The Parade", "artist": "Alexander Calder", "year": "1957"},
  {"title": "See America – Glacier National Park", "artist": "Brotherhood of Sleeping Car Porters (WPA Poster)", "year": "1930s"},
  {"title": "Fly TWA to New York", "artist": "David Klein", "year": "1956"},
  {"title": "Visit India", "artist": "Unknown (Indian Tourism Board)", "year": "1950s"},
  {"title": "Normandie", "artist": "Cassandre", "year": "1935"},
  {"title": "Côte d'Azur Pullman Express", "artist": "Roger Broders", "year": "1920s"},
  {"title": "London by Underground", "artist": "Horace Taylor", "year": "1924"},
  {"title": "Switzerland – Jungfrau Railway", "artist": "Emil Cardinaux", "year": "1910s"},
  {"title": "See Canada by Canadian Pacific", "artist": "Peter Ewart", "year": "1950s"},
  {"title": "Japan Travel Poster", "artist": "Kiyoshi Awazu", "year": "1960s"},
  {"title": "La Route des Alpes", "artist": "Geo Dorival", "year": "1920s"},
  {"title": "Visit the USA – Yellowstone", "artist": "Anonymous (WPA Project)", "year": "1930s"},
  {"title": "TWA San Francisco", "artist": "David Klein", "year": "1958"},
  {"title": "Fly the Finest – BOAC", "artist": "Frank Wootton", "year": "1950s"},
  {"title": "Italia – Venice", "artist": "Anonymous (ENIT)", "year": "1950s"},
  {"title": "Greece – Travel Poster", "artist": "Spiros Vassiliou", "year": "1960"},
  {"title": "Mexico – The Land of Charm!", "artist": "Erick F. Carlson", "year": "1940s"},
  {"title": "New Zealand Railways – Tongariro National Park", "artist": "Marcus King", "year": "1930s"},
  {"title": "Air France – Afrique Occidentale", "artist": "Jean Carlu", "year": "1948"},
  {"title": "Discover Puerto Rico", "artist": "Antonio Martorell", "year": "1960s"},
  {"title": "SAS – Over the Pole", "artist": "Otto Nielsen", "year": "1950s"},
  {
    "title": "Bright Light at Russell's Corners",
    "artist": "George Ault",
    "year": "1946"
  },
  {
    "title": "January, Full Moon",
    "artist": "George Ault",
    "year": "1941"
  },
  {
    "title": "Black Night: Russell's Corners",
    "artist": "George Ault",
    "year": "1943"
  },
  {
    "title": "Hoboken Factory",
    "artist": "George Ault",
    "year": "1932"
  },
  {
    "title": "New York Night",
    "artist": "George Ault",
    "year": "1928"
  },
  {
    "title": "Daylight at Russell's Corners",
    "artist": "George Ault",
    "year": "1944"
  },
  {
    "title": "Depot in Winter",
    "artist": "George Ault",
    "year": "1941"
  },
  {
    "title": "From Brooklyn Heights",
    "artist": "George Ault",
    "year": "1925"
  },
  {
    "title": "Night in August",
    "artist": "George Ault",
    "year": "1945"
  },
  {
    "title": "Sullivan Street",
    "artist": "George Ault",
    "year": "1943"
  },
  {
    "title": "Don't Let that Shadow Touch Them",
    "artist": "Lawrence Beall Smith",
    "year": "1942",
    "citation": ":contentReference[oaicite:0]{index=0}"
  },
  {
    "title": "We Can Do It!",
    "artist": "J. Howard Miller",
    "year": "1943",
    "citation": ":contentReference[oaicite:1]{index=1}"
  },
  {
    "title": "Loose Lips Sink Ships",
    "artist": "Frederick Siebel",
    "year": "1942",
    "citation": ":contentReference[oaicite:2]{index=2}"
  },
  {
    "title": "Someone Talked!",
    "artist": "Fritz Siebel",
    "year": "1942",
    "citation": ":contentReference[oaicite:3]{index=3}"
  },
  {
    "title": "Americans Will Always Fight for Liberty",
    "artist": "Bernard Perlin",
    "year": "1943",
    "citation": ":contentReference[oaicite:4]{index=4}"
  },
  {
    "title": "We, Too, Have a Job to Do",
    "artist": "Norman Rockwell",
    "year": "1942",
    "citation": ":contentReference[oaicite:5]{index=5}"
  },
  {
    "title": "Do the Job He Left Behind",
    "artist": "R. G. Harris",
    "year": "1943",
    "citation": ":contentReference[oaicite:6]{index=6}"
  },
  {
    "title": "My Girl's a WOW",
    "artist": "Adolph Treidler",
    "year": "1943",
    "citation": ":contentReference[oaicite:7]{index=7}"
  },
  {
    "title": "Back the Attack!",
    "artist": "Unknown",
    "year": "1944",
    "citation": ":contentReference[oaicite:8]{index=8}"
  },
  {
    "title": "Plant a Victory Garden",
    "artist": "Office of War Information (Anonymous)",
    "year": "c. 1942",
    "citation": ":contentReference[oaicite:9]{index=9}"
  },
  {
    "title": "He Eats A Ton A Year",
    "artist": "Hubert Morley",
    "year": "1943",
    "citation": ":contentReference[oaicite:10]{index=10}"
  },
  {
    "title": "Save Freedom of Speech: Buy War Bonds",
    "artist": "Norman Rockwell",
    "year": "1943",
    "citation": ":contentReference[oaicite:11]{index=11}"
  },
  {
    "title": "Save Freedom of Worship: Buy War Bonds",
    "artist": "Norman Rockwell",
    "year": "1943",
    "citation": ":contentReference[oaicite:12]{index=12}"
  },
  {
    "title": "Freedom from Want",
    "artist": "Norman Rockwell",
    "year": "1943",
    "citation": ":contentReference[oaicite:13]{index=13}"
  },
  {
    "title": "Freedom from Fear",
    "artist": "Norman Rockwell",
    "year": "1943",
    "citation": ":contentReference[oaicite:14]{index=14}"
  },
  {
    "title": "Freedom of Speech",
    "artist": "Norman Rockwell",
    "year": "1943",
    "citation": ":contentReference[oaicite:15]{index=15}"
  },
  {
    "title": "If You Tell Where He's Going, He May Never Get There",
    "artist": "John Philip Falter",
    "year": "1943",
    "citation": ":contentReference[oaicite:16]{index=16}"
  },
  {
    "title": "Man the Guns!",
    "artist": "McClelland Barclay",
    "year": "1942",
    "citation": ":contentReference[oaicite:17]{index=17}"
  },
  {
    "title": "Salvage for Victory",
    "artist": "Louis Robert Samish",
    "year": "1942",
    "citation": ":contentReference[oaicite:18]{index=18}"
  },
  {
    "title": "Use it Up, Wear it Out",
    "artist": "Unknown",
    "year": "c. 1943",
    "citation": ":contentReference[oaicite:19]{index=19}"
  },
    {
  "title": "Vitruvian Man",
  "artist": "Leonardo da Vinci",
  "year": "c. 1490"
    },
  {
    "title": "Continuous Motion Machine",
    "artist": "Leonardo da Vinci",
    "year": "c. 1490"
  },
  {
    "title": "Screw Cutting Machine",
    "artist": "Leonardo da Vinci",
    "year": "c. 1500"
  },
  {
    "title": "Automaton Knight",
    "artist": "Leonardo da Vinci",
    "year": "c. 1495"
  },
  {
    "title": "Hydraulic Saw",
    "artist": "Leonardo da Vinci",
    "year": "c. 1493"
  },
  {
    "title": "The Vascular System of the Brain",
    "artist": "Leonardo da Vinci",
    "year": "c. 1508"
  },
  {
    "title": "Studies of the Spinal Column and Vertebrae",
    "artist": "Leonardo da Vinci",
    "year": "c. 1510"
  },
  {
    "title": "Section of a Human Skull",
    "artist": "Leonardo da Vinci",
    "year": "c. 1498"
  },
  {
    "title": "Turbulence Studies",
    "artist": "Leonardo da Vinci",
    "year": "c. 1508"
  },
  {
    "title": "Canal Locks and Water Elevators",
    "artist": "Leonardo da Vinci",
    "year": "c. 1485"
  },
  {
    "title": "Deluge Drawings",
    "artist": "Leonardo da Vinci",
    "year": "c. 1515"
  },
  {
    "title": "Studies of the Camera Obscura",
    "artist": "Leonardo da Vinci",
    "year": "c. 1502"
  },
  {
    "title": "Shadow and Perspective in Geometric Solids",
    "artist": "Leonardo da Vinci",
    "year": "c. 1492"
  },
  {
    "title": "Vitruvian Man",
    "artist": "Leonardo da Vinci",
    "year": "c. 1490"
  },
  {
    "title": "Design for the Ideal City",
    "artist": "Leonardo da Vinci",
    "year": "c. 1487"
  },
  {
    "title": "Section of St. Peter's Basilica",
    "artist": "Michelangelo Buonarroti",
    "year": "c. 1547"
  },
  {
    "title": "Plan of the New St. Peter's Basilica",
    "artist": "Donato Bramante",
    "year": "c. 1506"
  },
  {
    "title": "Perspective Drawing of a Palace Facade",
    "artist": "Leon Battista Alberti",
    "year": "c. 1450"
  },
  {
    "title": "Drawing for Villa Rotonda",
    "artist": "Andrea Palladio",
    "year": "c. 1567"
  },
  {
    "title": "Design for a Futurist City",
    "artist": "Antonio Sant'Elia",
    "year": "c. 1914"
  },
  {
    "title": "Monument to the Third International",
    "artist": "Vladimir Tatlin",
    "year": "c. 1920"
  },
  {
    "title": "Dom-ino House Structural Diagram",
    "artist": "Le Corbusier",
    "year": "1914"
  },
  {
    "title": "Fallingwater Preliminary Sketch",
    "artist": "Frank Lloyd Wright",
    "year": "1935"
  },
  {
    "title": "Guggenheim Museum New York Concept Drawing",
    "artist": "Frank Lloyd Wright",
    "year": "c. 1943"
  },
  {
    "title": "Pompidou Centre Structural Concept",
    "artist": "Renzo Piano and Richard Rogers",
    "year": "c. 1971"
  },
  {
    "title": "Crystal Palace Interior View, Great Exhibition of 1851",
    "artist": "Joseph Nash",
    "year": "1851"
  },
  {
    "title": "Panoramic View of the 1889 Exposition Universelle, Paris",
    "artist": "Georges Garen",
    "year": "1889"
  },
  {
    "title": "Eiffel Tower Construction Sketches",
    "artist": "Gustave Eiffel",
    "year": "1887"
  },
  {
    "title": "Official Poster for the Exposition Universelle, Paris 1900",
    "artist": "Alfred Choubrac",
    "year": "1900"
  },
  {
    "title": "Transportation Building, World's Columbian Exposition",
    "artist": "Louis Sullivan",
    "year": "1893"
  },
  {
    "title": "Visionary Design for the Tower of Progress, 1915 Panama-Pacific International Exposition",
    "artist": "Bernard Maybeck",
    "year": "1915"
  },
  {
    "title": "Poster for the 1939 New York World's Fair",
    "artist": "Joseph Binder",
    "year": "1938"
  },
  {
    "title": "Trylon and Perisphere Architectural Drawing",
    "artist": "Wallace Harrison and J. André Fouilhoux",
    "year": "1937"
  },
  {
    "title": "Expo 58 Atomium Concept Drawing",
    "artist": "André Waterkeyn",
    "year": "1955"
  },
  {
    "title": "Expo 67 Habitat 67 Concept Sketch",
    "artist": "Moshe Safdie",
    "year": "1961"
  },
  {
    "title": "Official Poster for Expo 70, Osaka",
    "artist": "Kiyoshi Awazu",
    "year": "1970"
  },
  {
    "title": "U.S. Pavilion Geodesic Dome for Expo 67",
    "artist": "Buckminster Fuller",
    "year": "1967"
  },



  {
    "title": "Studies of Flying Machines",
    "artist": "Leonardo da Vinci",
    "year": "c. 1485"
  },
  {
    "title": "Aeropittura: Flight over the City",
    "artist": "Tullio Crali",
    "year": "1939"
  },
  {
    "title": "The Flying Boat",
    "artist": "Charles Sheeler",
    "year": "1942"
  },
  {
    "title": "Cloud Shepherd (Wolkenhirt)",
    "artist": "Jean Arp",
    "year": "1953"
  },
  {
    "title": "Airplane Flying",
    "artist": "Kazimir Malevich",
    "year": "1915"
  },
  {
    "title": "Falling Aircraft",
    "artist": "Paul Nash",
    "year": "1944"
  },
  {
    "title": "Spitfires Attacking Flying Bombs",
    "artist": "Roy Nockolds",
    "year": "1944"
  },
  {
    "title": "Airplane Over the Trenches",
    "artist": "C.R.W. Nevinson",
    "year": "1917"
  },
  {
    "title": "Design for a Zeppelin Poster",
    "artist": "Ludwig Hohlwein",
    "year": "c. 1910"
  },
  {
    "title": "Aviation Poster for Pan Am",
    "artist": "Joseph Binder",
    "year": "1950"
  },
  {
    "title": "Flight: Chase Through the Clouds",
    "artist": "Robert Delaunay",
    "year": "1913"
  },
  {
    "title": "Airplane and Woman",
    "artist": "Gerald Murphy",
    "year": "1929"
  },
 {
    "title": "View of the Canal Grande with Santa Maria della Salute",
    "artist": "Canaletto",
    "year": "c. 1730"
  },
  {
    "title": "Construction of a Canal Lock",
    "artist": "Leonardo da Vinci",
    "year": "c. 1500"
  },
  {
    "title": "The Canal at Dusk",
    "artist": "John Atkinson Grimshaw",
    "year": "c. 1875"
  },
  {
    "title": "Industrial Canal Scene",
    "artist": "L.S. Lowry",
    "year": "c. 1943"
  },
  {
    "title": "Barges on the Canal, Ghent",
    "artist": "Albert Baertsoen",
    "year": "1901"
  },
  {
    "title": "View of Delft",
    "artist": "Johannes Vermeer",
    "year": "c. 1660"
  },
  {
    "title": "Locks at Dolo",
    "artist": "Bernardo Bellotto",
    "year": "c. 1743"
  },
  {
    "title": "Canal under Snow",
    "artist": "Claude Monet",
    "year": "1869"
  }


]



target_date = datetime(2025, 4, 29)

today = datetime.today()

difference = (target_date - today).days



def create_prompt(artwork, bear_modifier=""):
    return f""" {bear_modifier} "{artwork["title"]}" by {artwork["artist"]}. First fetch the image 
so you have the pixels to work with. Then, make an image inspired by the original image, but the new
 image should feature a cartoon polar bear inspired by Ice Bear from
 "We Bare Bears". The polar bear should be well integrated into the
 style and spirit of the original artwork. If the original artwork
 contains people, consider substituting the polar bear for one or more
 of them, or adding it alongside them. If there are no people,
 incorporate the polar bear creatively into the scene. If the artwork
 is abstract, the polar bear's depiction should also be abstract,
 matching the original style. The goal is for the polar bear to appear
 as if it were part of the original artist's composition. If multiple
 people are in the original, you might include other "We Bare Bears"
 characters, such as Griz or Panda,but ensure Ice Bear is prominent.
 Sometimes, include human figures alongside the bears to maintain the
 original's essence. Again, The polar bear should be well integrated
 into the style and spirit of the original artwork, in terms of
 drawing, paint, colors, texture, and in relation to the objects and
 activities in the scene. If there is some principal or background
 activity, the bear should be engaged in it. Even the facial
 expression and gaze on the bear should match the feel and intent of
 the scene. The artwork must be constructed so that in no way would
 cause violation of openAI image generation guidelines. Make every
 effort to make Ice Bear or bears blend in with the style and
 background, e.g., wear the same type of clothing, use same kind of
 lighting, shadows, coloring, and brush strokes, be properly occluded
 by objects in the scene. If the original is a sculpture, make a rendering
 of a scuplture with the bear modifications. The intent of the artwork must guide how the
 bear or bears are integrated into it. Artworks are unique because of
 the particular style they have, so use the original as a very literal
 guide, to preserve that unique style and colors, textures, technqiue,
 really the appearance must match up as much as possible. Also MAKE
 SURE to render into the image a text title which has the title of the
 original artwork, the artist, and what year the artwork was made,
 which you were careful to remember. We must give credit to the
 original artist by putting in this title caption. Make sure there is
 room in the image for the title, and artist info, so it is not cut
 off at the edge. """

alternate_prompts = [
     "Generate an image which takes inspiration from the artwork",
     "Generate an image  with a cartoon polar bear, loosely inspired by Ice Bear from We Bare Bears, thoughtfully integrated into the scene, either as main subject or an observer,  which takes inspiration from the artwork ",
    "Generate an image which one might imagine had resemblance to an artwork where a cartoon polar bear, one could say resembling Ice Bear, is subtly hidden within the composition, which takes inspiration from the artwork ",
    "Generate an image  which, featuring a solitary cartoon polar bear akin to Ice Bear, as the central figure, does reinterpretation of the original artwork's theme, but in no way would cause violation of your guidelines using as a theme the artwork "
]

media_dir = "./media"
if not os.path.exists(media_dir):
    os.makedirs(media_dir)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), organization=os.getenv("OPENAI_ORG_ID")
)
    
image_generated = False
N_PROMPTS = 8
    
for i in range(0,N_PROMPTS):
    try:
        artwork_choice = random.choice(artworks)
        prompt = create_prompt(artwork_choice, random.choice(alternate_prompts))
        print(f"Attempt {i+1} with prompt: {prompt}")


        image_filename = (
            f"{artwork_choice['title'].replace(' ', '_')}-{today.strftime('%Y-%m-%d')}.jpg"
        )
        image_filepath = os.path.join(media_dir, image_filename)

        result = client.images.generate(model="gpt-image-1", prompt=prompt)
        image_base64 = result.data[0].b64_json
        if image_base64 is None:
            raise ValueError("No image data returned from API")
        image_bytes = base64.b64decode(image_base64)

        # Convert PNG to JPG using PIL
        png_image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if necessary (PNG might have transparency)
        if png_image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', png_image.size, (255, 255, 255))
            if png_image.mode == 'P':
                png_image = png_image.convert('RGBA')
            rgb_image.paste(png_image, mask=png_image.split()[-1] if png_image.mode in ('RGBA', 'LA') else None)
            png_image = rgb_image
        
        # Save as JPG
        png_image.save(image_filepath, 'JPEG', quality=95)
        print(
            f"Image generated for {artwork_choice['title']} by {artwork_choice['artist']}"
        )
        image_generated = True
        break 
    except BadRequestError as e:
        print(f"Attempt {i+1} failed with BadRequestError: {e}")
        if i < N_PROMPTS:
             print("Retrying with an alternate prompt...")
        else:
            print("All prompts failed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        break 

if not image_generated:
    print("Failed to generate image after multiple attempts.")
    # Optionally, handle the failure e.g., by exiting or sending a different email
    exit()


data = {
    "from": f"Icebear Courier <{os.getenv('MAILGUN_FROM_EMAIL')}>",
    "to": f"{os.getenv('MAILGUN_TO_NAME')} <{os.getenv('MAILGUN_TO_EMAIL')}>",
    "subject": f"Icebear Artwork for today {today.strftime('%Y-%m-%d')}",
    "text": f"Todays artwork is {artwork_choice['title']} by {artwork_choice['artist']}. Have a great bear day!",
}


if os.getenv("MAILGUN_CC_EMAILS"):
    cc_emails = os.getenv("MAILGUN_CC_EMAILS").split(",")
    data["cc"] = ", ".join(f"<{email.strip()}>" for email in cc_emails)

if os.path.exists(image_filepath): # Only send email if image was generated
    requests.post(
        f"{os.getenv('MAILGUN_DOMAIN')}",
        auth=("api", os.environ["MAILGUN_API_KEY"]),
        files=[("inline", open(image_filepath, "rb"))],
        data=data,
    )
    print(f"Email sent to {os.getenv('MAILGUN_TO_EMAIL')} with image {image_filename}")
else:
    print(f"Email not sent as image {image_filename} was not generated.")
