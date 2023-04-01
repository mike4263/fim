fim - fortune improved
======================
<img src="logo.png"  width="400" height="400">

<img src="demo/kirk.gif" alt="your_alternative_text" loop=infinite>

Its 2023.  It's time for a modern https://en.wikipedia.org/wiki/Fortune_(Unix)[fortune] replacement, now with ChatGPT integration!

In case you aren't familiar with the classic utility from `bsdgames`, fortune came from a time before the internet or even https://en.wikipedia.org/wiki/Gopher_(protocol)[Gopher] when people had to derive all their pleasure from terminal utilities.  It is a way of displaying epigrams - a pithy saying or remark expressing an idea in a clever and amusing way.  It was a time when engineers wore pocket protecters and wrote man pages with words like epigrams in them.

This project had been on indefinite pause until ChatGPT came out and I decided to add support.  It is really quite facsinating interacting with the epigrams and watching it describe them.  Over time, we'll add more support for GPT prompts and becoming a CLI client with rich history tracking.

`fim` records all of your impressions into a local SQLite DB.  It uses BucketSort(TM) to guarantees a weighted distribution and _guarantees_ content will be displayed without repeats. `fim` currently supports about 13k epigrams from old `fortune` files.  Content is provided via a submodule to https://github.com/mike4263/fim-content[fim-content].

FimGPT
======

Sometimes, the output is just bizarre or foreign.  Never fear!  We can ask ChatGPT!

```
% fim --openai $OPENAI_ACCESS_TOKEN --gpt

42

   > "42" is a classic epigram from the science fiction book series "The
   > Hitchhiker's Guide to the Galaxy" by Douglas Adams. In the story, a group
   > of hyper-intelligent beings create a supercomputer called Deep Thought and
   > task it with finding the answer to the ultimate question of life, the
   > universe, and everything. The computer takes 7.5 million years to calculate
   > the answer, which turns out to be 42. However, no one knows what the actual
   > question was that led to this answer, leaving the characters and readers
   > puzzled and amused.
   > The humor in the epigram lies in its absurdity and the fact that it is a
   > non-answer to a supposedly profound question. It has become a popular
   > cultural reference among fans of sci-fi and internet culture, often used as
   > a shorthand for a seemingly meaningful but ultimately meaningless answer to
   > a question. It has also been referenced in various films, TV shows, and

```


And, sometimes you will get creepy foreshadowing of our impending AI takeover with omnious takes such as:

```


... A booming voice says, "Wrong, cretin!", and you notice that you
have turned into a pile of dust.

   > This epigram is a humorous warning about the consequences of giving a wrong
   > answer to a computer or artificial intelligence. It suggests that the
   > computer may respond with extreme, unexpected actions to someone who is
   > incorrect or mistaken in their input, as represented by the transformation
   > into dust.
   > It is unclear if there are any specific references to individuals or
   > popular culture in this epigram. The language and tone are reminiscent of
   > science fiction and fantasy works, where powerful and dangerous beings
   > often hold immense power and are easily angered. However, it may also
   > simply be an example of computer-related humor common in the early days of
   > computing.
   > Overall, this epigram serves as a reminder to approach technology with
   > caution and respect, and to be careful with the input we provide.


```


```
% fim

The use of anthropomorphic terminology when dealing with computing systems
is a symptom of professional immaturity.
		-- Edsger Dijkstra
```


```

% fim context

The use of anthropomorphic terminology when dealing with computing systems
is a symptom of professional immaturity.
		-- Edsger Dijkstra

   > This epigram is a witty observation by computer scientist Edsger Dijkstra
   > on the tendency of people to refer to their computing systems in human
   > terms, such as "intelligent" or "stupid." Dijkstra argues that this is
   > evidence of a lack of professionalism in the industry, as it demonstrates a
   > childish and irrational approach to technology.
   > The reference to "anthropomorphic terminology" refers to the use of
   > human-like characteristics to describe non-human entities, such as
   > computers. Dijkstra criticizes this habit, suggesting that it is indicative
   > of the field's immaturity and lack of rigor.
   > Edsger Dijkstra was a Dutch computer scientist who made important
   > contributions to the field of software engineering. He was known for his
   > work on the development of programming languages and algorithms. He won the
   > Turing Award, one of the most prestigious honors in computer science, in
   > 1972.
   > This epigram is often cited in discussions of computer science and
   > technology, particularly in debates over the role of artificial
   > intelligence and the potential for technological singularity. It has also
   > been referenced in popular culture, such as in the TV show "Person of
   > Interest," where a character quotes the epigram in an episode about the
   > dangers of artificial intelligence.

```

Getting Started
===============

```
podman run quay.io/mike4263/fim:latest
```
