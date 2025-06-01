from openai import OpenAI, BadRequestError
import os
import base64
import random
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

artworks = [
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
    {"title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "c. 1503–1506"},
    {"title": "Dubonnet", "artist": "A. M. Cassandre", "year": "1932"},
    {"title": "The Garden of Love", "artist": "Peter Paul Rubens", "year": "1633"},
    {"title": "The Fighting Temeraire", "artist": "J.M.W. Turner", "year": "1839"},
    {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
    {"title": "Ophelia", "artist": "John Everett Millais", "year": "1851–1852"},
    {"title": "The Man with the Golden Arm", "artist": "Saul Bass", "year": "1955"},
    {"title": "La Loïe Fuller", "artist": "Jules Chéret", "year": "1893"},
    {"title": "Starry Night", "artist": "Vincent van Gogh", "year": "1889"},
    {"title": "24 Heures du Mans", "artist": "A. M. Cassandre", "year": "1931"},
    {"title": "Hope", "artist": "Shepard Fairey", "year": "2008"},
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
    {"title": "The Last Supper", "artist": "Leonardo da Vinci", "year": "c. 1495–1498"},
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
  {"title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "1503"},
  {"title": "The Last Supper", "artist": "Leonardo da Vinci", "year": "1498"},
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
  {"title": "Balloon Dog (Orange)", "artist": "Jeff Koons", "year": "2000"},
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
  {"title": "Afghan Girl", "artist": "Steve McCurry", "year": "1984"},
  {"title": "Tank Man", "artist": "Jeff Widener", "year": "1989"},
  {"title": "V-J Day in Times Square", "artist": "Alfred Eisenstaedt", "year": "1945"},
  {"title": "The Tetons and the Snake River", "artist": "Ansel Adams", "year": "1942"},
  {"title": "Lunch atop a Skyscraper", "artist": "Charles C. Ebbets", "year": "1932"},
  {"title": "Earthrise", "artist": "William Anders", "year": "1968"},
  {"title": "Napalm Girl", "artist": "Nick Ut", "year": "1972"},
  {"title": "The Steerage", "artist": "Alfred Stieglitz", "year": "1907"},
 {"title": "Madonna with the Long Neck", "artist": "Parmigianino", "year": "1535"},
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

]

target_date = datetime(2025, 4, 29)

today = datetime.today()

difference = (target_date - today).days

artwork_choice = random.choice(artworks)

def create_prompt(artwork, bear_modifier=""):
    return f"""
 {bear_modifier} "{artwork["title"]}" by {artwork["artist"]}.
The image should feature a cartoon polar bear inspired by Ice Bear from "We Bare Bears".
The polar bear should be integrated into the style and spirit of the original artwork.
If the original artwork contains people, consider substituting the polar bear for one or more of them, or adding it alongside them.
If there are no people, incorporate the polar bear creatively into the scene.
If the artwork is abstract, the polar bear's depiction should also be abstract, matching the original style.
The goal is for the polar bear to appear as if it were part of the original artist's composition.
If multiple people are in the original, you might include other "We Bare Bears" characters, but ensure Ice Bear is prominent.
Sometimes, include human figures alongside the bears to maintain the original's essence.
"""

alternate_prompts = [
     "Generate an image which takes inspiration from the artwork",
     "Generate an image  with a cartoon polar bear, loosely inspired by Ice Bear from We Bare Bears, thoughtfully integrated into the scene, either as main subject or an observer,  which takes inspiration from the artwork ",
    "Generate an image which one might imagine had resemblance to an artwork where a cartoon polar bear, one could say resembling Ice Bear, is subtly hidden within the composition, which takes inspiration from the artwork ",
    "Generate an image  which, featuring a solitary cartoon polar bear akin to Ice Bear, as the central figure, does reinterpretation of the original artwork's theme, but in no way would cause violation of your guidelines using as a theme the artwork "
]

prompt_modifier = random.choice(alternate_prompts)
initial_prompt = create_prompt(artwork_choice, prompt_modifier)

media_dir = "./media"
if not os.path.exists(media_dir):
    os.makedirs(media_dir)

image_filename = (
    f"{artwork_choice['title'].replace(' ', '_')}-{today.strftime('%Y-%m-%d')}.png"
)
image_filepath = os.path.join(media_dir, image_filename)

if not os.path.exists(image_filepath):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), organization=os.getenv("OPENAI_ORG_ID")
    )
    
    prompts_to_try = [initial_prompt] + list(map(lambda prompt: create_prompt(artwork_choice, prompt), alternate_prompts))

    image_generated = False
    
    for i, current_prompt in enumerate(prompts_to_try):
        if i >= 3: # Max 3 retries (initial + 2 alternates)
            print("Maximum retries reached. Could not generate image.")
            break
        try:
            print(f"Attempt {i+1} with prompt: {current_prompt}")
            result = client.images.generate(model="gpt-image-1", prompt=current_prompt)
            image_base64 = result.data[0].b64_json
            if image_base64 is None:
                raise ValueError("No image data returned from API")
            image_bytes = base64.b64decode(image_base64)

            with open(image_filepath, "wb") as f:
                f.write(image_bytes)
            print(
                f"Image generated for {artwork_choice['title']} by {artwork_choice['artist']}"
            )
            image_generated = True
            break 
        except BadRequestError as e:
            print(f"Attempt {i+1} failed with BadRequestError: {e}")
            if i < len(prompts_to_try) -1:
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
